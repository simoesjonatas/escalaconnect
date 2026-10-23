import { router } from 'expo-router';

import { useEquipes } from './hooks';
import { useTema } from './tema';
import { Botao, Cartao, Etiqueta, Subtitulo, Texto } from './ui';

/**
 * Para quem ainda não é membro aprovado de nenhuma equipe: a disponibilidade só
 * pode ser informada depois que a liderança aprova a entrada (o servidor recusa antes).
 */
export function AvisoSemEquipe() {
  const pendentes = useEquipes().data?.pendentes ?? [];
  const { cores } = useTema();
  const aguardando = pendentes.length > 0;
  return (
    <Cartao style={{ borderColor: cores.pendente, borderWidth: 2 }}>
      {aguardando && <Etiqueta texto="Aguardando aprovação" cor={cores.pendente} />}
      <Subtitulo>{aguardando ? 'Seu pedido foi enviado' : 'Entre em uma equipe'}</Subtitulo>
      <Texto>
        {aguardando
          ? `A liderança de ${pendentes.map((e) => e.nome).join(', ')} vai analisar seu pedido. Depois da aprovação você já pode informar sua disponibilidade.`
          : 'Para informar sua disponibilidade e ser escalado, peça para entrar em uma equipe e aguarde a aprovação da liderança.'}
      </Texto>
      <Botao
        titulo={aguardando ? 'Ver minhas equipes' : 'Escolher equipe'}
        variante={aguardando ? 'secundario' : 'primario'}
        aoTocar={() => router.push('/equipes')}
      />
    </Cartao>
  );
}
