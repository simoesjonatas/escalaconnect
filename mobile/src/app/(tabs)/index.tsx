import { router } from 'expo-router';

import { useAuth } from '../../lib/auth';
import { CartaoDeEscala } from '../../lib/escala-ui';
import { useHome } from '../../lib/hooks';
import { Botao, Cartao, Estado, Suave, Subtitulo, Tela, Texto, Titulo } from '../../lib/ui';

export default function Inicio() {
  const { usuario } = useAuth();
  const home = useHome();
  const dados = home.data;

  return (
    <Tela atualizando={home.isRefetching} aoAtualizar={() => home.refetch()}>
      <Titulo>Olá, {usuario?.first_name || usuario?.username}</Titulo>
      <Estado consulta={home} />
      {dados && (
        <>
          {dados.escalas_pendentes > 0 && (
            <Cartao>
              <Subtitulo>
                {dados.escalas_pendentes === 1
                  ? 'Você tem 1 escala a confirmar'
                  : `Você tem ${dados.escalas_pendentes} escalas a confirmar`}
              </Subtitulo>
              <Botao titulo="Ver minhas escalas" aoTocar={() => router.navigate('/escalas')} />
            </Cartao>
          )}

          <Subtitulo>Próxima escala</Subtitulo>
          {dados.proxima_escala ? (
            <CartaoDeEscala escala={dados.proxima_escala} />
          ) : (
            <Suave>Você não tem escalas futuras.</Suave>
          )}

          {!dados.tem_disponibilidade && (
            <Cartao>
              <Subtitulo>Informe sua disponibilidade</Subtitulo>
              <Texto>Sem ela, a liderança não sabe quando pode contar com você.</Texto>
              <Botao
                titulo="Informar disponibilidade"
                variante="secundario"
                aoTocar={() => router.navigate('/disponibilidade')}
              />
            </Cartao>
          )}

          {(dados.falta_email || dados.falta_telefone) && (
            <Cartao>
              <Subtitulo>Complete seu contato</Subtitulo>
              <Texto>
                {dados.falta_email && dados.falta_telefone
                  ? 'Faltam seu e-mail e seu telefone com DDD.'
                  : dados.falta_email
                    ? 'Falta seu e-mail.'
                    : 'Falta seu telefone com DDD.'}
              </Texto>
              <Botao titulo="Atualizar contato" variante="secundario" aoTocar={() => router.push('/contato')} />
            </Cartao>
          )}
        </>
      )}
    </Tela>
  );
}
