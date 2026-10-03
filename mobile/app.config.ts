import { existsSync } from 'node:fs';

import { ConfigContext, ExpoConfig } from 'expo/config';

// Complementa o app.json com o que depende do perfil de build (ver eas.json).
export default ({ config }: ConfigContext): ExpoConfig => {
  const desenvolvimento = process.env.APP_VARIANT === 'development';
  // Baixado do projeto Firebase (necessário para o push no Android). Enquanto o
  // arquivo não existir, o app compila normalmente, só não recebe push.
  const googleServices = './google-services.json';
  return {
    ...(config as ExpoConfig),
    android: {
      ...config.android,
      ...(existsSync(googleServices) ? { googleServicesFile: googleServices } : {}),
    },
    plugins: [
      ...(config.plugins ?? []),
      // Em desenvolvimento o app fala com o runserver local por HTTP (http://10.0.2.2:8000 no emulador).
      // Nos demais perfis só HTTPS é permitido.
      ['expo-build-properties', { android: { usesCleartextTraffic: desenvolvimento } }],
    ],
  };
};
