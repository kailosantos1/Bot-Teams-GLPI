# bot/attachments.py
"""
Baixa attachments enviados pelo usuário no Teams.
Suporte aprimorado para imagens coladas (Ctrl+V) com detecção de tipo real via bytes mágicos.
"""

import mimetypes
import requests
from config import logger, settings


def _detect_image_type(file_bytes: bytes) -> str | None:
    """
    Detecta o tipo de imagem a partir dos bytes iniciais (magic bytes).
    Retorna a extensão (sem o ponto) ou None se não reconhecer.
    """
    if len(file_bytes) < 8:
        return None

    # PNG: \x89PNG\r\n\x1a\n
    if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    # JPEG: \xFF\xD8\xFF
    if file_bytes[:3] == b'\xFF\xD8\xFF':
        return 'jpg'
    # GIF: GIF87a ou GIF89a
    if file_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    # BMP: BM
    if file_bytes[:2] == b'BM':
        return 'bmp'
    # WebP: RIFF....WEBP
    if file_bytes[:4] == b'RIFF' and len(file_bytes) >= 12 and file_bytes[8:12] == b'WEBP':
        return 'webp'
    # TIFF: MM (big-endian) ou II (little-endian)
    if file_bytes[:2] in (b'MM', b'II'):
        return 'tiff'
    return None


class TeamsAttachmentHandler:

    @staticmethod
    async def download_attachments(turn_context) -> list[tuple[str, bytes]]:
        """
        Percorre os attachments da activity atual e baixa o binário de cada um.
        Retorna lista de (filename, bytes).
        """
        activity = turn_context.activity
        attachments = getattr(activity, "attachments", None) or []
        result = []

        if not attachments:
            return result

        token = None

        for att in attachments:
            content_type = att.content_type or ""
            name = att.name or "anexo"

            try:
                # -----------------------------------------------------
                # Arquivo "de verdade" (via clipe) -- não precisa de token
                # -----------------------------------------------------
                if content_type == "application/vnd.microsoft.teams.file.download.info":
                    download_url = att.content.get("downloadUrl") if isinstance(att.content, dict) else None
                    if not download_url:
                        logger.warning(f"Anexo '{name}' sem downloadUrl, ignorando")
                        continue

                    res = requests.get(download_url, timeout=30)
                    if res.status_code == 200:
                        result.append((name, res.content))
                        logger.info(f"📎 Anexo baixado: {name} ({len(res.content)} bytes)")
                    else:
                        logger.warning(f"Falha ao baixar anexo '{name}': status {res.status_code}")
                    continue

                # -----------------------------------------------------
                # Conteúdo com content_url (imagens coladas, etc.)
                # -----------------------------------------------------
                if getattr(att, "content_url", None):
                    if token is None:
                        token = await TeamsAttachmentHandler._get_bot_access_token(turn_context)

                    if not token:
                        logger.warning(f"Sem token disponível, não foi possível baixar '{name}'")
                        continue

                    dl_headers = {"Authorization": f"Bearer {token}"}
                    logger.info(f"🔽 Baixando de: {att.content_url[:80]}...")
                    res = requests.get(att.content_url, headers=dl_headers, timeout=30)

                    if res.status_code == 200:
                        file_bytes = res.content
                        real_content_type = res.headers.get("Content-Type", "").split(";")[0].strip()

                        # 1. Tenta obter extensão pelo Content-Type real
                        ext = mimetypes.guess_extension(real_content_type) or ""

                        # 2. Se não conseguiu ou é genérico (ex: .bin), tenta detectar com bytes mágicos
                        if not ext or ext == ".bin":
                            detected = _detect_image_type(file_bytes)
                            if detected:
                                ext = f".{detected}"
                                logger.info(f"🔍 Tipo detectado por magic bytes: {detected}")
                            else:
                                # Fallback: se o nome original tiver uma extensão, usa ela
                                if name and "." in name:
                                    ext = "." + name.split(".")[-1]
                                else:
                                    ext = ".bin"  # último fallback

                        # Define o nome final
                        base_name = name
                        # Se o nome não tiver extensão, ou for muito genérico, usa um nome padrão
                        if not base_name or base_name == "anexo" or "." not in base_name:
                            base_name = "imagem_colada"
                        # Se já tem extensão, mantém, senão adiciona a detectada
                        if "." not in base_name:
                            filename = f"{base_name}{ext}"
                        else:
                            # Se já tem extensão mas queremos garantir que é a correta, podemos substituir
                            # Para simplificar, mantemos a original se tiver extensão válida
                            # Mas se a extensão for .bin, substituímos pela detectada
                            base, old_ext = base_name.rsplit(".", 1)
                            if old_ext.lower() == "bin" and ext and ext != ".bin":
                                filename = f"{base}{ext}"
                            else:
                                filename = base_name

                        result.append((filename, file_bytes))
                        logger.info(
                            f"🖼️ Conteúdo baixado: {filename} "
                            f"({len(file_bytes)} bytes, tipo real='{real_content_type}', extensão='{ext}')"
                        )
                    else:
                        logger.warning(f"Falha ao baixar '{name}': status {res.status_code} - url: {att.content_url[:80]}...")
                    continue

                logger.info(f"Anexo '{name}' ignorado (tipo '{content_type}' não suportado)")

            except Exception as e:
                logger.warning(f"Erro ao baixar anexo '{name}': {e}")

        return result

    @staticmethod
    async def _get_bot_access_token(turn_context) -> str | None:
        """
        Obtém token OAuth usando credenciais do bot diretamente do settings.
        """
        try:
            from botframework.connector.auth import MicrosoftAppCredentials

            app_id = settings.MICROSOFT_APP_ID
            app_password = settings.MICROSOFT_APP_PASSWORD
            tenant = settings.MICROSOFT_APP_TENANT_ID

            if not app_id or not app_password:
                logger.warning("MicrosoftAppId/Password não configurados no .env")
                return None

            credentials = MicrosoftAppCredentials(
                app_id,
                app_password,
                channel_auth_tenant=tenant,
            )
            token = credentials.get_access_token()
            logger.info("✅ Token OAuth obtido com sucesso via settings")
            return token

        except Exception as e:
            logger.warning(f"Não foi possível obter token: {e}")
            return None