import { addMonths, format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { useState } from 'react';
import { Alert, Linking } from 'react-native';

import { ChipsDeEscolha } from '../../lib/formulario-lider';
import { semAcento } from '../../lib/texto';
import { useLinkDoPdf, useOpcoesDeEventos } from '../../lib/hooks';
import { PedidoDePdf } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Suave, Tela } from '../../lib/ui';

// Mesmos estilos do "Exportar PDF" do site.
const ESTILOS: { valor: PedidoDePdf['estilo']; rotulo: string; descricao: string }[] = [
  { valor: 'connect', rotulo: 'Connect', descricao: 'Claro, identidade do app' },
  { valor: 'escuro', rotulo: 'Escuro', descricao: 'Visual do app, ideal para tela' },
  { valor: 'mural', rotulo: 'Mural', descricao: 'P&B, grande, para imprimir' },
];

/** Mês passado, este e os dois seguintes ('AAAA-MM'). */
const MESES = [-1, 0, 1, 2].map((n) => {
  const d = addMonths(new Date(), n);
  const rotulo = format(d, 'MMMM/yyyy', { locale: ptBR });
  return { valor: format(d, 'yyyy-MM'), rotulo: rotulo.charAt(0).toUpperCase() + rotulo.slice(1) };
});

/** "Recepção" + "2026-11" -> "escala-recepcao-2026-11.pdf" */
const nomeDoArquivo = (equipe: string, mes: string) =>
  `escala-${semAcento(equipe)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')}-${mes}.pdf`;

/** O mesmo PDF da escala do site: baixa e abre o compartilhar do celular (WhatsApp, salvar, imprimir). */
export default function PdfDaEscala() {
  const opcoes = useOpcoesDeEventos();
  const link = useLinkDoPdf();
  const [equipe, setEquipe] = useState<number>();
  const [mes, setMes] = useState(MESES[1].valor);
  const [estilo, setEstilo] = useState<PedidoDePdf['estilo']>('connect');
  const [baixando, setBaixando] = useState(false);
  const [destino, setDestino] = useState<'compartilhar' | 'navegador'>('compartilhar');

  const dados = opcoes.data;
  const equipeId = equipe ?? dados?.equipes[0]?.id;
  const nomeDaEquipe = dados?.equipes.find((e) => e.id === equipeId)?.nome ?? 'equipe';

  async function compartilhar(url: string) {
    setBaixando(true);
    try {
      const arquivo = new File(Paths.cache, nomeDoArquivo(nomeDaEquipe, mes));
      const baixado = await File.downloadFileAsync(url, arquivo, { idempotent: true });
      await Sharing.shareAsync(baixado.uri, {
        mimeType: 'application/pdf',
        UTI: 'com.adobe.pdf',
        dialogTitle: `Escala ${nomeDaEquipe}`,
      });
    } catch {
      Alert.alert('PDF', 'Não foi possível baixar o PDF. Tente de novo ou abra no navegador.');
    } finally {
      setBaixando(false);
    }
  }

  function gerar(para: 'compartilhar' | 'navegador') {
    if (!equipeId) return;
    setDestino(para);
    const [ano, numero] = mes.split('-').map(Number);
    link.mutate(
      { equipe_id: equipeId, ano, mes: numero, estilo },
      {
        onSuccess: ({ url }) =>
          para === 'compartilhar'
            ? void compartilhar(url)
            : Linking.openURL(url).catch(() =>
                Alert.alert('PDF', 'Não foi possível abrir o navegador neste aparelho.'),
              ),
      },
    );
  }

  return (
    <Tela>
      <Estado consulta={opcoes} vazio={dados?.equipes.length === 0 && 'Você não lidera nenhuma equipe.'} />
      {dados && dados.equipes.length > 0 && (
        <>
          <Cartao style={{ gap: 14 }}>
            {dados.equipes.length > 1 && (
              <ChipsDeEscolha
                titulo="Equipe"
                opcoes={dados.equipes.map((e) => ({ valor: e.id, rotulo: e.nome }))}
                ativas={equipeId ? [equipeId] : []}
                aoTocar={setEquipe}
              />
            )}
            <ChipsDeEscolha titulo="Mês" opcoes={MESES} ativas={[mes]} aoTocar={setMes} />
            <ChipsDeEscolha
              titulo="Estilo do PDF"
              opcoes={ESTILOS}
              ativas={[estilo]}
              aoTocar={setEstilo}
              dica={ESTILOS.find((e) => e.valor === estilo)?.descricao}
            />
          </Cartao>
          <Erro erro={link.error} />
          <Botao
            titulo="Compartilhar PDF"
            carregando={(link.isPending && destino === 'compartilhar') || baixando}
            aoTocar={() => gerar('compartilhar')}
          />
          <Botao
            titulo="Abrir no navegador"
            variante="secundario"
            carregando={link.isPending && destino === 'navegador'}
            aoTocar={() => gerar('navegador')}
          />
          <Suave>Compartilhar abre as opções do celular: mandar no WhatsApp, salvar em Arquivos ou imprimir.</Suave>
        </>
      )}
    </Tela>
  );
}
