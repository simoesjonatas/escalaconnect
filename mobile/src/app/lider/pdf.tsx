import { addMonths, format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useState } from 'react';
import { Alert, Linking } from 'react-native';

import { ChipsDeEscolha } from '../../lib/formulario-lider';
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

/** O mesmo PDF da escala do site, aberto no navegador do celular (de lá dá para salvar ou compartilhar). */
export default function PdfDaEscala() {
  const opcoes = useOpcoesDeEventos();
  const link = useLinkDoPdf();
  const [equipe, setEquipe] = useState<number>();
  const [mes, setMes] = useState(MESES[1].valor);
  const [estilo, setEstilo] = useState<PedidoDePdf['estilo']>('connect');

  const dados = opcoes.data;
  const equipeId = equipe ?? dados?.equipes[0]?.id;

  function abrir() {
    if (!equipeId) return;
    const [ano, numero] = mes.split('-').map(Number);
    link.mutate(
      { equipe_id: equipeId, ano, mes: numero, estilo },
      {
        onSuccess: ({ url }) =>
          Linking.openURL(url).catch(() => Alert.alert('PDF', 'Não foi possível abrir o navegador neste aparelho.')),
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
          <Suave>O PDF abre no navegador. De lá, use o botão de compartilhar para salvar ou mandar no WhatsApp.</Suave>
          <Erro erro={link.error} />
          <Botao titulo="Abrir PDF da escala" carregando={link.isPending} aoTocar={abrir} />
        </>
      )}
    </Tela>
  );
}
