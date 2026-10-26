"""Inspeção local sem configuração, credenciais ou rede."""
import importlib.metadata
import inspect
import sys
import platform


def main():
    print('Python:', platform.python_version())
    print('Interpretador:', sys.executable)
    missing = False
    for package in ('botbuilder-core', 'botbuilder-schema', 'botframework-connector'):
        try:
            print(package, importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            print(package, 'não instalado')
            missing = True
    if missing:
        print('Compatibilidade não confirmada; executar no ambiente que inicia o bot.')
        return 1
    try:
        from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, BotAdapter
        from botbuilder.schema import Activity, ConversationAccount
        from botbuilder.core.teams import TeamsInfo
        from botbuilder.schema.teams import TeamsChannelAccount
        from botframework.connector.auth import ClaimsIdentity, SimpleCredentialProvider
        for method in (TeamsInfo.get_member, BotFrameworkAdapter.process_activity,
                       BotFrameworkAdapterSettings, ClaimsIdentity, SimpleCredentialProvider):
            print(method.__name__, inspect.signature(method))
        for model in (Activity, ConversationAccount, TeamsChannelAccount):
            print(model.__name__, 'fields:', sorted(model._attribute_map))
        print('identity key:', BotAdapter.BOT_IDENTITY_KEY)
    except ImportError:
        print('SDK não instalado neste interpretador; conferir no ambiente de implantação.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
