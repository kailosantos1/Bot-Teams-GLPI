# bot/glpi_auth.py
"""
Busca informações do usuário no GLPI para validação.
Apenas usuários com email cadastrado no GLPI são autorizados.
Com cache de tempo limitado e lock para segurança.
"""

import requests
import json
import time
import threading
from typing import Optional, List
from config import settings, logger


class GLPIAuthService:
    """Serviço para buscar usuários no GLPI."""
    
    def __init__(self):
        self.url = settings.GLPI_URL.rstrip('/')
        self.app_token = settings.GLPI_APP_TOKEN
        self.user_token = settings.GLPI_USER_TOKEN
        
        # Sessão
        self._session_token = None
        self._session_expires_at = 0
        
        # Cache de usuários
        self._users_cache = None
        self._users_cache_time = 0
        self._users_cache_ttl = 600  # 10 minutos
        
        # Cache de grupos
        self._groups_cache = {}
        self._groups_cache_time = {}
        self._groups_cache_ttl = 600  # 10 minutos
        
        # Lock para evitar buscas simultâneas
        self._lock = threading.Lock()
    
    def _get_session(self) -> Optional[str]:
        """Inicia sessão no GLPI (com verificação de expiração)."""
        # Verifica se a sessão ainda é válida (25 minutos)
        if self._session_token and time.time() < self._session_expires_at:
            return self._session_token
        
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Authorization": f"user_token {self.user_token}"
        }
        
        try:
            res = requests.post(f"{self.url}/initSession", headers=headers, timeout=10)
            if res.status_code == 200:
                self._session_token = res.json().get("session_token")
                # Sessão GLPI expira em ~30 min, usamos 25 min por segurança
                self._session_expires_at = time.time() + 1500
                logger.info("✅ Nova sessão GLPI iniciada")
                return self._session_token
            return None
        except Exception as e:
            logger.error(f"Erro na sessão GLPI: {e}")
            return None
    
    def _get_headers(self) -> dict:
        """Retorna headers para requisições."""
        return {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": self._session_token
        }
    
    def _list_all_users(self) -> list:
        """
        Lista todos os usuários do GLPI (com lock e TTL).
        """
        # Verifica se o cache é válido (fora do lock - rápido)
        if (self._users_cache is not None and 
            (time.time() - self._users_cache_time) < self._users_cache_ttl):
            logger.info(f"📦 Cache válido ({len(self._users_cache)} usuários)")
            return self._users_cache
        
        # Usa lock para evitar múltiplas buscas simultâneas
        with self._lock:
            # Verifica NOVAMENTE dentro do lock (outra thread pode ter buscado)
            if (self._users_cache is not None and 
                (time.time() - self._users_cache_time) < self._users_cache_ttl):
                logger.info(f"📦 Cache válido (verificado dentro do lock)")
                return self._users_cache
            
            session_token = self._get_session()
            
            if not session_token:
                logger.error("Sem sessão GLPI")
                return []
            
            headers = self._get_headers()
            
            all_users = []
            start = 0
            limit = 100
            
            try:
                while True:
                    url = f"{self.url}/User"
                    params = {"range": f"{start}-{start + limit - 1}"}
                    
                    res = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if res.status_code in [200, 206]:
                        users = res.json()
                        
                        if isinstance(users, list) and users:
                            all_users.extend(users)
                            
                            if len(users) < limit:
                                break
                            start += limit
                        else:
                            break
                    else:
                        logger.error(f"Erro ao listar: {res.status_code}")
                        break
                
                # Atualiza o cache com timestamp
                self._users_cache = all_users
                self._users_cache_time = time.time()
                logger.info(f"✅ {len(all_users)} usuários carregados (cache por {self._users_cache_ttl}s)")
                return all_users
                
            except Exception as e:
                logger.error(f"Erro ao listar usuários: {e}")
                return []
    
    def search_user_by_name(self, name: str) -> Optional[str]:
        """Busca email do usuário pelo nome no GLPI."""
        users = self._list_all_users()
        
        if not users:
            logger.warning("Nenhum usuário listado")
            return None
        
        name_normalized = name.lower().replace(".", "").replace(" ", "")
        logger.info(f"🔍 Buscando '{name}' (normalizado: '{name_normalized}')")
        
        for user in users:
            firstname = user.get('firstname') or ''
            realname = user.get('realname') or ''
            name_field = user.get('name') or ''
            
            full_name_1 = f"{firstname} {realname}".strip()
            full_name_2 = f"{realname} {firstname}".strip()
            
            full_name_1_norm = full_name_1.lower().replace(".", "").replace(" ", "")
            full_name_2_norm = full_name_2.lower().replace(".", "").replace(" ", "")
            name_field_norm = name_field.lower().replace(".", "").replace(" ", "")
            realname_norm = realname.lower().replace(".", "").replace(" ", "")
            firstname_norm = firstname.lower().replace(".", "").replace(" ", "")
            
            if (name_normalized in full_name_1_norm or 
                name_normalized in full_name_2_norm or
                name_normalized in name_field_norm or
                name_normalized in realname_norm or
                name_normalized in firstname_norm):
                
                logger.info(f"✅ USUÁRIO ENCONTRADO NO GLPI")
                logger.info(f"  id: {user.get('id')}")
                logger.info(f"  firstname: {firstname}")
                logger.info(f"  realname: {realname}")
                logger.info(f"  name (login): {name_field}")
                
                user_id = user.get('id')
                if user_id:
                    email = self._get_user_email_by_id(user_id)
                    if email:
                        logger.info(f"✅ Email cadastrado: {email}")
                        return email
                    else:
                        logger.warning(f"⚠️ Usuário NÃO tem email cadastrado no GLPI")
                        return None
        
        logger.warning(f"❌ Usuário não encontrado no GLPI: {name}")
        return None
    
    def _get_user_email_by_id(self, user_id: int) -> Optional[str]:
        """Busca email do usuário pelo ID (SEM cache - sempre busca)."""
        headers = self._get_headers()
        
        try:
            email_url = f"{self.url}/User/{user_id}/UserEmail"
            email_res = requests.get(email_url, headers=headers, timeout=10)
            
            if email_res.status_code in [200, 206]:
                emails_data = email_res.json()
                
                if isinstance(emails_data, list) and emails_data:
                    for email_item in emails_data:
                        if isinstance(email_item, dict):
                            for field in ['email', 'mail', 'address']:
                                if field in email_item and email_item[field]:
                                    return email_item[field]
                
                elif isinstance(emails_data, dict):
                    for field in ['email', 'mail', 'address']:
                        if field in emails_data and emails_data[field]:
                            return emails_data[field]
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar email: {e}")
            return None
    
    def get_user_email(self, name: str) -> Optional[str]:
        """Busca email do usuário pelo nome."""
        return self.search_user_by_name(name)
    
    def get_user_groups_by_email(self, email: str) -> List[str]:
        """
        Busca os grupos do usuário pelo email no GLPI.
        SEMPRE busca em tempo real (sem cache para segurança).
        """
        session_token = self._get_session()
        
        if not session_token:
            logger.error("Sem sessão GLPI para buscar grupos")
            return []
        
        headers = self._get_headers()
        
        # Encontra o ID do usuário pelo email
        user_id = self._find_user_id_by_email(email)
        
        if not user_id:
            logger.warning(f"Usuário não encontrado pelo email: {email}")
            return []
        
        logger.info(f"🔍 Buscando grupos do usuário ID {user_id}...")
        
        try:
            # Usa o endpoint CORRETO: /User/{id}/Group_User
            groups_url = f"{self.url}/User/{user_id}/Group_User"
            
            logger.info(f"URL: {groups_url}")
            
            res = requests.get(groups_url, headers=headers, timeout=10)
            
            logger.info(f"Status: {res.status_code}")
            
            if res.status_code in [200, 206]:
                group_user_data = res.json()
                group_names = []
                
                if isinstance(group_user_data, list):
                    for relation in group_user_data:
                        if isinstance(relation, dict):
                            group_id = relation.get('groups_id')
                            
                            if group_id:
                                group_name = self._get_group_name_by_id(group_id, headers)
                                
                                if group_name:
                                    group_names.append(group_name)
                                    logger.info(f"  ✅ Grupo: {group_name} (ID: {group_id})")
                
                logger.info(f"✅ Total de {len(group_names)} grupo(s)")
                return group_names
            else:
                logger.warning(f"Erro: {res.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar grupos: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _find_user_id_by_email(self, email: str) -> Optional[int]:
        """Encontra o ID do usuário pelo email."""
        users = self._list_all_users()
        
        if not users:
            return None
        
        email_normalized = email.lower().strip()
        
        for user in users:
            user_id = user.get('id')
            
            if not user_id:
                continue
            
            user_email = self._get_user_email_by_id(user_id)
            
            if user_email and user_email.lower().strip() == email_normalized:
                logger.info(f"✅ Usuário encontrado: ID={user_id}, Email={user_email}")
                return user_id
        
        logger.warning(f"❌ Usuário não encontrado pelo email: {email}")
        return None
    
    def _get_group_name_by_id(self, group_id: int, headers: dict) -> Optional[str]:
        """Busca o nome do grupo pelo ID (com cache de 10 min)."""
        # Verifica cache
        if group_id in self._groups_cache:
            cache_time = self._groups_cache_time.get(group_id, 0)
            if (time.time() - cache_time) < self._groups_cache_ttl:
                return self._groups_cache[group_id]
        
        try:
            group_url = f"{self.url}/Group/{group_id}"
            
            res = requests.get(group_url, headers=headers, timeout=5)
            
            if res.status_code in [200, 206]:
                group_data = res.json()
                
                if isinstance(group_data, dict):
                    group_name = (
                        group_data.get('name') or 
                        group_data.get('completename') or 
                        ''
                    )
                    
                    if group_name:
                        # Atualiza cache
                        self._groups_cache[group_id] = group_name
                        self._groups_cache_time[group_id] = time.time()
                        return group_name
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao buscar grupo {group_id}: {e}")
            return None


# Instância global
glpi_auth = GLPIAuthService()