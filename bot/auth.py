# bot/auth.py
"""
Módulo de autenticação e autorização do bot.
Valida se o usuário tem permissão para usar o bot baseado no domínio do email.
Fonte de dados: GLPI (email cadastrado no usuário e grupos).
"""

from typing import Optional, Tuple
from config import logger
from bot.glpi_auth import glpi_auth


class UserAuthorization:
    """Classe responsável por validar a autorização dos usuários."""
    
    # Domínios permitidos
    ALLOWED_DOMAINS = [
        "compasi.com.br",
        "systemup.inf.br",
    ]
    
    # Grupos do GLPI que podem acessar o formulário de CADASTRO
    CADASTRO_ALLOWED_GROUPS = [
        "Recursos Humanos",
        "RH",
        "TI",
        "Gerencia",
        # Adicione mais nomes de grupos conforme necessário
    ]
    
    # Emails autorizados individualmente (fallback se não estiver em nenhum grupo)
    CADASTRO_ALLOWED_EMAILS = [
        "rodrigues.genes@compasi.com.br",      # TI
        # Adicione mais emails conforme necessário
    ]
    
    @classmethod
    def extract_display_name(cls, activity) -> Optional[str]:
        """Extrai o nome de exibição do usuário do Teams."""
        from_property = activity.from_property if hasattr(activity, 'from_property') else None
        
        if from_property and hasattr(from_property, 'name'):
            return from_property.name
        
        return None
    
    @classmethod
    def extract_email(cls, activity) -> Optional[str]:
        """Extrai email do usuário buscando no GLPI pelo nome."""
        display_name = cls.extract_display_name(activity)
        
        if not display_name:
            logger.error("Nome do usuário não encontrado")
            return None
        
        logger.info(f"🔍 Buscando email para: '{display_name}'")
        
        try:
            email = glpi_auth.get_user_email(display_name)
            if email:
                logger.info(f"✅ Email via GLPI: {email}")
                return email
        except Exception as e:
            logger.error(f"Erro ao buscar no GLPI: {e}")
        
        logger.warning(f"❌ Email não encontrado para: {display_name}")
        return None
    
    @classmethod
    def extract_domain(cls, email: str) -> Optional[str]:
        """Extrai o domínio do email."""
        if not email or "@" not in email:
            return None
        
        domain = email.split("@")[1].lower().strip()
        
        if not domain:
            return None
        
        return domain
    
    @classmethod
    def is_domain_allowed(cls, email: str) -> bool:
        """Verifica se o domínio é permitido."""
        if not email or "@" not in email:
            return False
        
        if email.split("@")[0].strip() == "":
            return False
        
        domain = cls.extract_domain(email)
        return domain in cls.ALLOWED_DOMAINS if domain else False
    
    @classmethod
    def can_access_cadastro(cls, email: str, display_name: str = None) -> bool:
        """
        Verifica se o usuário tem permissão para acessar o formulário de cadastro.
        
        Ordem de verificação:
        1. Email na lista de autorizados (rápido)
        2. Grupos do GLPI (fonte principal)
        
        Args:
            email: Email do usuário
            display_name: Nome de exibição (para log)
        
        Returns:
            True se pode acessar, False caso contrário
        """
        if not email:
            logger.warning("Email vazio - acesso negado ao cadastro")
            return False
        
        email_lower = email.lower().strip()
        
        # 1. Verifica se o email está na lista de autorizados
        if email_lower in [e.lower() for e in cls.CADASTRO_ALLOWED_EMAILS]:
            logger.info(f"✅ Acesso ao cadastro LIBERADO (email na lista): {email}")
            return True
        
        # 2. Busca os grupos do usuário no GLPI
        logger.info(f"🔍 Buscando grupos do usuário no GLPI: {email}")
        
        try:
            user_groups = glpi_auth.get_user_groups_by_email(email)
            
            if user_groups:
                logger.info(f"📋 Grupos do usuário: {user_groups}")
                
                # Verifica se algum grupo está na lista de permitidos
                for grupo in user_groups:
                    grupo_lower = grupo.lower().strip()
                    
                    for allowed_group in cls.CADASTRO_ALLOWED_GROUPS:
                        allowed_lower = allowed_group.lower().strip()
                        
                        # Verifica se o nome do grupo contém o grupo permitido ou vice-versa
                        if allowed_lower in grupo_lower or grupo_lower in allowed_lower:
                            logger.info(f"✅ Acesso LIBERADO (grupo '{grupo}'): {email}")
                            return True
            else:
                logger.warning(f"Usuário sem grupos no GLPI: {email}")
                
        except Exception as e:
            logger.error(f"Erro ao buscar grupos do usuário: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 3. Nega acesso
        logger.warning(f"⛔ Acesso ao cadastro NEGADO: {email}")
        return False
    
    @classmethod
    def validate_user(cls, activity) -> Tuple[bool, Optional[str], str]:
        """Valida se o usuário tem permissão para usar o bot."""
        email = cls.extract_email(activity)
        
        return cls.validate_user_with_email(email)
    
    @classmethod
    def validate_user_with_email(cls, email: str) -> Tuple[bool, Optional[str], str]:
        """Valida um email diretamente."""
        if not email:
            return False, None, (
                "❌ **Não foi possível identificar seu email.**\n\n"
                "Seu usuário não possui email cadastrado no GLPI.\n"
                "Contate o suporte de TI para cadastrar seu email."
            )
        
        if not cls.is_domain_allowed(email):
            domain = cls.extract_domain(email) or "desconhecido"
            logger.warning(f"Acesso negado para domínio: {domain}")
            return False, email, (
                "⛔ **Acesso negado.**\n\n"
                "Seu email não está autorizado a usar este bot.\n\n"
                "Se você acredita que isso é um erro, "
                "contate o suporte de TI para mais informações."
            )
        
        logger.info(f"✅ Usuário autorizado: {email}")
        return True, email, f"✅ Usuário autorizado: {email}"


# Instância global
user_auth = UserAuthorization()