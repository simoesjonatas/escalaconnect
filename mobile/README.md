# Escala Connect — app do voluntário

App React Native (Expo SDK 57, TypeScript) que consome a API `/api/v1/` do backend Django
deste repositório (app `api/`). Android primeiro; o mesmo código serve para iOS.

## O que o app faz (v1, só voluntário)

Login, primeiro acesso (definir senha e aceitar o termo), início com pendências, minhas
escalas (confirmar, sinalizar impedimento, pedir/cancelar troca), calendário, disponibilidade
pelos eventos (como no site), minhas equipes, contato e troca de senha. Tema claro/escuro segue o
aparelho. Líder e admin usam o site.

## Estrutura

- `src/app/` — telas (Expo Router). `_layout.tsx` decide o grupo de telas pelo estado da sessão.
- `src/lib/api.ts` — cliente da API (token no SecureStore; 401 volta ao login; 403
  `senha_pendente`/`termo_pendente` abre a tela correspondente).
- `src/lib/hooks.ts` — consultas e mutações (TanStack Query).
- `src/lib/push.ts` — registro do aparelho (`POST /devices/`) e a tela que cada push abre ao toque.
- `src/lib/versao.tsx` — `BUILD_ATUAL`, comparado com `APP_MIN_BUILD` do servidor.

## Desenvolvimento

O app usa módulos nativos que o Expo Go não traz: é preciso um *development build*.

```bash
npm install
npx tsc --noEmit                      # checagem de tipos
npx expo export --platform android    # confere se o bundle compila
```

Backend local para o app (na raiz do repositório):

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

No emulador Android o servidor local é `http://10.0.2.2:8000` (já configurado no perfil
`development` do `eas.json`); inclua `10.0.2.2` em `ALLOWED_HOSTS`. Em aparelho físico,
use o IP da máquina na rede em `EXPO_PUBLIC_API_URL`.

## Builds (EAS)

Uma vez, com uma conta Expo:

```bash
npx eas-cli@latest login
npx eas-cli@latest init            # cria o projeto e grava o projectId
npx eas-cli@latest update:configure  # grava a URL de atualizações pelo ar
```

Para o push no Android (uma vez):

1. Crie um projeto no Firebase e adicione um app Android com o pacote `br.org.pibvp.connect`.
2. Baixe o `google-services.json` para esta pasta (`mobile/`).
3. Gere uma chave de conta de serviço (FCM V1) no Firebase e envie com
   `npx eas-cli@latest credentials` (Android → Google Service Account → FCM V1).

Push não funciona no Expo Go nem em emulador sem Google Play: teste com um build em aparelho físico.

Depois:

```bash
npx eas-cli@latest build --profile development --platform android   # build de desenvolvimento
npx eas-cli@latest build --profile preview --platform android       # APK para distribuir
npx eas-cli@latest update --channel preview --message "..."         # atualização pelo ar (só JS)
```

Mudança nativa (biblioteca nova, permissão) exige APK novo: aumente `BUILD_ATUAL` no app e
`APP_MIN_BUILD` no `.env` do servidor, e informe o link em `APP_APK_URL`.
