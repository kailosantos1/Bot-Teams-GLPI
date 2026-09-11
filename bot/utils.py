# bot/utils.py
import unicodedata
from typing import Optional
from datetime import datetime
import random


class UserNameFormatter:
    """Utilitário para extrair e formatar nomes de usuários do Teams."""
    
    @staticmethod
    def extract_first_name(user_name: Optional[str]) -> str:
        """Extrai o primeiro nome do usuário."""
        if not user_name or user_name == "Usuário Teams":
            return "Usuário"
        if "@" in user_name:
            user_name = user_name.split("@")[0]
        if "." in user_name:
            user_name = user_name.split(".")[0]
        if " " in user_name:
            user_name = user_name.split(" ")[0]
        if not user_name or user_name.lower() in ["user", "usuario", "usuário", "unknown"]:
            return "Usuário"
        user_name = UserNameFormatter.remove_accents(user_name)
        return UserNameFormatter._capitalize_name(user_name)
    
    @staticmethod
    def extract_full_name(user_name: Optional[str]) -> str:
        """Extrai o nome completo."""
        if not user_name or user_name == "Usuário Teams":
            return "Usuário"
        if "@" in user_name:
            user_name = user_name.split("@")[0]
        user_name = user_name.replace(".", " ").replace("_", " ")
        words = user_name.split()
        capitalized_words = [UserNameFormatter._capitalize_name(word) for word in words]
        return " ".join(capitalized_words)
    
    @staticmethod
    def _capitalize_name(name: str) -> str:
        """Capitaliza o nome."""
        if not name:
            return ""
        return name[0].upper() + name[1:] if len(name) > 1 else name.upper()
    
    @staticmethod
    def remove_accents(text: str) -> str:
        """Remove acentos."""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    @staticmethod
    def get_greeting(user_name: Optional[str] = None) -> str:
        """Saudação simples com horário."""
        hour = datetime.now().hour
        first_name = UserNameFormatter.extract_first_name(user_name)
        if 5 <= hour < 12:
            return f"Bom dia, {first_name}! ☀️"
        elif 12 <= hour < 18:
            return f"Boa tarde, {first_name}! 🌤️"
        else:
            return f"Boa noite, {first_name}! 🌙"
    
    @staticmethod
    def format_greeting_with_emoji(user_name: Optional[str] = None) -> str:
        """
        Saudação com emoji e instrução de uso, incluindo FlexSmart.
        """
        hour = datetime.now().hour
        first_name = UserNameFormatter.extract_first_name(user_name)
        
        greetings = {
            "morning": [
                f"☀️ Bom dia, {first_name}!",
                f"🌅 Olá, {first_name}!",
                f"👋 Bom dia, {first_name}!",
                f"😊 Olá, {first_name}!"
            ],
            "afternoon": [
                f"🌤️ Boa tarde, {first_name}!",
                f"👋 Olá, {first_name}!",
                f"💼 Boa tarde, {first_name}!",
                f"😊 Olá, {first_name}!"
            ],
            "evening": [
                f"🌙 Boa noite, {first_name}!",
                f"✨ Olá, {first_name}!",
                f"🌆 Boa noite, {first_name}!",
                f"😊 Olá, {first_name}!"
            ]
        }
        
        if 5 <= hour < 12:
            saudacao = random.choice(greetings["morning"])
        elif 12 <= hour < 18:
            saudacao = random.choice(greetings["afternoon"])
        else:
            saudacao = random.choice(greetings["evening"])
        
        instrucao = (
            f"\n\n**Como posso te ajudar?**\n\n"
            f"📝 *Descreva seu problema para começarmos o atendimento.*\n\n"
            f"**Exemplos:**\n"
            f"• 'Preciso de manutenção no meu PC'\n"
            f"• 'Erro na impressora'\n"
            f"• 'Cadastrar novo colaborador'\n"
            f"• 'Problema no FlexSmart'\n\n"
            f"Ou digite **'ajuda'** para ver todos os comandos."
        )
        
        return saudacao + instrucao