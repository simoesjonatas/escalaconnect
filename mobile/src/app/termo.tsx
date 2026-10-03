import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';

import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Usuario } from '../lib/types';
import { Botao, Cartao, Erro, Estado, Subtitulo, Suave, Tela, Texto, Titulo } from '../lib/ui';

type Bloco = { tipo: 'titulo' | 'paragrafo' | 'item'; texto: string };

/**
 * O termo vem da API como o mesmo trecho HTML simples do site (h3, p, li).
 * Converte em blocos de texto para não depender de um renderizador de HTML.
 */
function blocosDoTermo(html: string): Bloco[] {
  const tipos = { h3: 'titulo', p: 'paragrafo', li: 'item' } as const;
  const blocos: Bloco[] = [];
  for (const [, tag, conteudo] of html.matchAll(/<(h3|p|li)[^>]*>([\s\S]*?)<\/\1>/g)) {
    const texto = conteudo.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
    if (texto) blocos.push({ tipo: tipos[tag as keyof typeof tipos], texto });
  }
  return blocos;
}

export default function Termo() {
  const { atualizarUsuario, sair } = useAuth();
  const termo = useQuery({ queryKey: ['termo'], queryFn: () => api<{ html: string }>('GET', '/termo/') });
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  async function aceitar() {
    setErro(null);
    setEnviando(true);
    try {
      await atualizarUsuario(await api<Usuario>('POST', '/me/aceitar-termo/'));
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <Tela comTopo>
      <Titulo>Termo de Compromisso do Voluntário</Titulo>
      <Suave>Para participar das escalas, leia e aceite o termo abaixo.</Suave>
      <Estado consulta={termo} />
      {termo.data && (
        <Cartao>
          {blocosDoTermo(termo.data.html).map((bloco, i) =>
            bloco.tipo === 'titulo' ? (
              <Subtitulo key={i}>{bloco.texto}</Subtitulo>
            ) : bloco.tipo === 'item' ? (
              <View key={i} style={{ flexDirection: 'row', gap: 8 }}>
                <Texto>•</Texto>
                <View style={{ flex: 1 }}>
                  <Texto>{bloco.texto}</Texto>
                </View>
              </View>
            ) : (
              <Texto key={i}>{bloco.texto}</Texto>
            ),
          )}
        </Cartao>
      )}
      <Erro erro={erro} />
      <Botao titulo="Li e aceito o termo" aoTocar={aceitar} carregando={enviando} desabilitado={!termo.data} />
      <Botao titulo="Sair" variante="secundario" aoTocar={sair} />
    </Tela>
  );
}
