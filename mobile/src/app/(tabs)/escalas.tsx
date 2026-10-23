import { router } from 'expo-router';

import { CartaoDeEscala } from '../../lib/escala-ui';
import { useEscalas, useHome } from '../../lib/hooks';
import { Botao, Estado, Tela } from '../../lib/ui';

export default function Escalas() {
  const escalas = useEscalas();
  const vagas = useHome().data?.vagas_abertas ?? 0;
  return (
    <Tela aoAtualizar={() => escalas.refetch()}>
      <Estado consulta={escalas} vazio={escalas.data?.length === 0 && 'Você não tem escalas futuras.'} />
      {escalas.data?.map((escala) => <CartaoDeEscala key={escala.id} escala={escala} />)}
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
