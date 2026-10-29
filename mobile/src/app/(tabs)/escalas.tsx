import { router } from 'expo-router';
import { useState } from 'react';

import { CartaoDeEscala } from '../../lib/escala-ui';
import { aplicar, CartaoDeFiltros, escolher, Filtro, filtrosDeEquipe, filtrosDePeriodo, TODOS } from '../../lib/filtros';
import { useEscalas, useHome } from '../../lib/hooks';
import { Escala } from '../../lib/types';
import { Botao, Estado, Tela } from '../../lib/ui';

const SITUACOES: Filtro<Escala>[] = [
  { valor: 'confirmar', rotulo: 'A confirmar', aplica: (e) => !e.confirmada && !e.tem_impedimento && !e.troca_pendente },
  { valor: 'confirmadas', rotulo: 'Confirmadas', aplica: (e) => e.confirmada && !e.tem_impedimento && !e.troca_pendente },
  { valor: 'pedidos', rotulo: 'Impedimento ou troca', aplica: (e) => e.tem_impedimento || e.troca_pendente },
];

export default function Escalas() {
  const escalas = useEscalas();
  const vagas = useHome().data?.vagas_abertas ?? 0;
  const [equipe, setEquipe] = useState(TODOS);
  const [quando, setQuando] = useState(TODOS);
  const [situacao, setSituacao] = useState(TODOS);

  // Mesmo esquema da Liderança: cada linha só oferece o que existe depois da anterior.
  const todas = escalas.data ?? [];
  const porEquipe = escolher(
    filtrosDeEquipe<Escala>(
      todas.map((e) => [e.equipe_id, e.equipe]),
      (e, id) => e.equipe_id === id,
    ),
    todas,
    equipe,
    true,
  );
  const daEquipe = aplicar(todas, porEquipe.ativo);
  const porPeriodo = escolher(filtrosDePeriodo<Escala>((e) => e.evento.data_inicio), daEquipe, quando);
  const doPeriodo = aplicar(daEquipe, porPeriodo.ativo);
  const porSituacao = escolher(SITUACOES, doPeriodo, situacao);
  const lista = aplicar(doPeriodo, porSituacao.ativo);

  function limparFiltros() {
    setEquipe(TODOS);
    setQuando(TODOS);
    setSituacao(TODOS);
  }

  return (
    <Tela aoAtualizar={() => escalas.refetch()}>
      <Estado consulta={escalas} vazio={escalas.data?.length === 0 && 'Você não tem escalas futuras.'} />
      <CartaoDeFiltros
        titulo="Filtrar escalas"
        nome={todas.length === 1 ? 'escala' : 'escalas'}
        linhas={[
          { titulo: 'Equipe', todos: 'Todas', escolha: porEquipe, aoEscolher: setEquipe },
          { titulo: 'Quando', todos: 'Qualquer data', escolha: porPeriodo, aoEscolher: setQuando },
          { titulo: 'Situação', todos: 'Todas', escolha: porSituacao, aoEscolher: setSituacao },
        ]}
        total={todas.length}
        mostrando={lista.length}
        aoLimpar={limparFiltros}
      />
      {lista.map((escala) => (
        <CartaoDeEscala key={escala.id} escala={escala} />
      ))}
      {vagas > 0 && (
        <Botao
          titulo={vagas === 1 ? 'Ver 1 vaga em aberto' : `Ver ${vagas} vagas em aberto`}
          variante="secundario"
          aoTocar={() => router.push('/vagas')}
        />
      )}
    </Tela>
  );
}
