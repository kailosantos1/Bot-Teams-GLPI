"""Local retention maintenance only. Never calls GLPI or Teams."""
import argparse
from identity.replies import ReplyStore


def main():
    parser = argparse.ArgumentParser(description='Limpa conteúdo expirado e metadados antigos de respostas.')
    parser.add_argument('--db', default='data/identity.sqlite3')
    args = parser.parse_args()
    store = ReplyStore(args.db)
    store.prepare()
    print('Limpeza local concluída.')


if __name__ == '__main__':
    main()
