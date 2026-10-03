import { CartaoDeEscala } from '../../lib/escala-ui';
import { useEscalas } from '../../lib/hooks';
import { Estado, Tela } from '../../lib/ui';

export default function Escalas() {
  const escalas = useEscalas();
  return (
    <Tela atualizando={escalas.isRefetching} aoAtualizar={() => escalas.refetch()}>
      <Estado consulta={escalas} vazio={escalas.data?.length === 0 && 'Você não tem escalas futuras.'} />
      {escalas.data?.map((escala) => <CartaoDeEscala key={escala.id} escala={escala} />)}
    </Tela>
  );
}
