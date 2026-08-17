# cadastrar_emails_glpi.py - Versão final
"""
Script para cadastrar emails automaticamente no GLPI.
Ignora usuários de sistema, logins inválidos e emails Gmail.
"""

import requests
import time
import unicodedata
from config import settings, logger


class GLPIEmailCadastro:
    """Cadastra emails automaticamente no GLPI."""
    
    def __init__(self):
        self.url = settings.GLPI_URL.rstrip('/')
        self.app_token = settings.GLPI_APP_TOKEN
        self.user_token = settings.GLPI_USER_TOKEN
        self.session_token = None
        
        # Lista de logins que NÃO devem ser alterados
        self.LOGINS_IGNORADOS = [
            'admin',
            'post-only',
            'tech',
            'user',
            'user.read',
        ]
        
        # Emails que NÃO devem ser alterados
        self.EMAILS_IGNORADOS = [
            'exemplo@domain.com',
            'exemplo@domain.com',
        ]
    
    def iniciar_sessao(self):
        """Inicia sessão no GLPI."""
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Authorization": f"user_token {self.user_token}"
        }
        
        res = requests.post(f"{self.url}/initSession", headers=headers, timeout=10)
        
        if res.status_code == 200:
            self.session_token = res.json().get("session_token")
            logger.info("✅ Sessão GLPI iniciada")
            return True
        return False
    
    def listar_usuarios(self):
        """Lista todos os usuários."""
        headers = self._get_headers()
        
        all_users = []
        start = 0
        limit = 100
        
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
                break
        
        return all_users
    
    def _get_headers(self):
        """Retorna headers."""
        return {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": self.session_token
        }
    
    def verificar_email_existente(self, user_id):
        """Verifica se já tem email cadastrado."""
        headers = self._get_headers()
        url = f"{self.url}/User/{user_id}/UserEmail"
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code in [200, 206]:
            emails = res.json()
            if isinstance(emails, list) and emails:
                return True, emails
            elif isinstance(emails, dict):
                return True, emails
        
        return False, None
    
    def normalizar_login(self, login):
        """
        Normaliza o login:
        - Remove acentos
        - Remove espaços extras
        - Converte para minúsculas
        """
        # Remove espaços extras
        login = login.strip()
        
        # Remove acentos
        login = unicodedata.normalize('NFD', login)
        login = login.encode('ASCII', 'ignore').decode('ASCII')
        
        # Substitui espaços por ponto
        login = login.replace(' ', '.')
        
        # Converte para minúsculas
        login = login.lower()
        
        return login
    
    def deve_ignorar(self, login, firstname, realname):
        """Verifica se deve ignorar este usuário."""
        login_lower = login.lower().strip()
        
        # 1. Verifica se está na lista de ignorados
        if login_lower in self.LOGINS_IGNORADOS:
            return True, "Usuário de sistema"
        
        # 2. Logins com espaço (nome completo)
        if ' ' in login.strip():
            return True, "Login com espaço (nome completo)"
        
        # 3. Logins com acento
        if any(c in login for c in 'áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ'):
            return True, "Login com acento"
        
        # 4. Logins muito curtos (menos de 3 caracteres)
        if len(login_normalizado := self.normalizar_login(login)) < 3:
            return True, "Login muito curto"
        
        return False, ""
    
    def montar_email(self, login):
        """Monta email a partir do login."""
        login_normalizado = self.normalizar_login(login)
        return f"{login_normalizado}@compasi.com.br"
    
    def cadastrar_email(self, user_id, email):
        """Cadastra email para o usuário."""
        headers = self._get_headers()
        url = f"{self.url}/User/{user_id}/UserEmail"
        
        payload = {
            "input": {
                "users_id": user_id,
                "email": email,
                "is_default": 1,
                "is_dynamic": 0
            }
        }
        
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if res.status_code in [200, 201]:
            logger.info(f"✅ Email cadastrado: {email}")
            return True
        else:
            logger.error(f"❌ Erro ao cadastrar {email}: {res.status_code}")
            logger.error(f"Resposta: {res.text[:200]}")
            return False
    
    def executar(self, dry_run=True):
        """Executa o cadastro."""
        if not self.iniciar_sessao():
            return
        
        usuarios = self.listar_usuarios()
        
        total_sem_email = 0
        total_com_email = 0
        total_ignorados = 0
        total_cadastrados = 0
        
        logger.info("="*80)
        logger.info("📋 ANÁLISE DOS USUÁRIOS")
        logger.info("="*80)
        
        for user in usuarios:
            user_id = user.get('id')
            firstname = user.get('firstname') or ''
            realname = user.get('realname') or ''
            login_name = user.get('name') or ''
            
            # Verifica se já tem email
            tem_email, emails = self.verificar_email_existente(user_id)
            
            if tem_email:
                total_com_email += 1
                
                # Pega o email atual
                email_atual = None
                if isinstance(emails, list) and emails:
                    email_atual = emails[0].get('email', '')
                
                # Verifica se é Gmail (não alterar)
                if email_atual and 'gmail.com' in email_atual:
                    logger.warning(f"⚠️ NÃO ALTERAR (Gmail): ID={user_id} | {firstname} {realname} | {email_atual}")
                elif email_atual in self.EMAILS_IGNORADOS:
                    logger.warning(f"⚠️ NÃO ALTERAR: ID={user_id} | {firstname} {realname} | {email_atual}")
                else:
                    logger.info(f"✅ JÁ TEM email: ID={user_id} | {firstname} {realname} | {email_atual}")
                
                continue
            
            # Não tem email - verifica se deve ignorar
            deve_ignorar, motivo = self.deve_ignorar(login_name, firstname, realname)
            
            if deve_ignorar:
                total_ignorados += 1
                logger.warning(f"⚠️ IGNORADO ({motivo}): ID={user_id} | {firstname} {realname} | Login: {login_name}")
                continue
            
            # Monta email
            email_montado = self.montar_email(login_name)
            
            logger.info(f"📝 SEM email: ID={user_id} | {firstname} {realname} | Login: {login_name}")
            logger.info(f"   → Email: {email_montado}")
            
            total_sem_email += 1
            
            if not dry_run:
                if self.cadastrar_email(user_id, email_montado):
                    total_cadastrados += 1
                    time.sleep(0.5)
            else:
                logger.info(f"   [DRY RUN] Seria cadastrado: {email_montado}")
        
        logger.info("="*80)
        logger.info("📊 RESUMO")
        logger.info("="*80)
        logger.info(f"Total de usuários: {len(usuarios)}")
        logger.info(f"Já tem email: {total_com_email}")
        logger.info(f"Sem email (cadastráveis): {total_sem_email}")
        logger.info(f"Ignorados: {total_ignorados}")
        logger.info(f"Cadastrados agora: {total_cadastrados}")
        logger.info("="*80)


if __name__ == "__main__":
    import sys
    
    dry_run = True
    
    if len(sys.argv) > 1 and sys.argv[1].lower() == "executar":
        dry_run = False
        print("⚠️ MODO EXECUÇÃO REAL!")
        print("⚠️ Isso vai CADASTRAR emails no GLPI de verdade!")
        print("⚠️ Tem certeza? Digite 'SIM' para continuar: ", end="")
        confirmacao = input().strip()
        
        if confirmacao != "SIM":
            print("❌ Cancelado!")
            sys.exit(0)
    
    service = GLPIEmailCadastro()
    service.executar(dry_run=dry_run)