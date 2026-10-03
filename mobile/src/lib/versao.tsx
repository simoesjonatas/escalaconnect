import { useQuery } from '@tanstack/react-query';
import { Linking } from 'react-native';

import { api } from './api';
import { Botao, Tela, Texto, Titulo } from './ui';

/**
 * Número deste build nativo. Aumente junto com APP_MIN_BUILD no servidor quando uma
 * mudança exigir APK novo (bibliotecas nativas, permissões): os aparelhos com build
 * menor passam a ver o aviso abaixo. Mudanças só de JavaScript vão por `eas update`.
 */
export const BUILD_ATUAL = 4;

type Meta = { min_build: number; apk_url: string };

/** Devolve os dados do servidor se este aparelho precisa instalar um APK mais novo. */
export function useAtualizacaoObrigatoria(): Meta | null {
  const meta = useQuery({ queryKey: ['meta'], queryFn: () => api<Meta>('GET', '/meta/'), staleTime: Infinity });
  return meta.data && meta.data.min_build > BUILD_ATUAL ? meta.data : null;
}

export function TelaDeAtualizacao({ meta }: { meta: Meta }) {
  return (
    <Tela comTopo>
      <Titulo>Atualize o aplicativo</Titulo>
      <Texto>Esta versão não funciona mais com o sistema. Instale a versão nova para continuar.</Texto>
      {!!meta.apk_url && <Botao titulo="Baixar a versão nova" aoTocar={() => void Linking.openURL(meta.apk_url)} />}
    </Tela>
  );
}
