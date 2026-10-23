import Ionicons from '@expo/vector-icons/Ionicons';
import { isSameDay } from 'date-fns';
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';

import { useAuth } from '../../lib/auth';
import { hora } from '../../lib/datas';
import { AvisoSemEquipe } from '../../lib/equipe-ui';
import { CartaoDeEscala } from '../../lib/escala-ui';
import { useAcaoDeEscala, useEscalas, useHome } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { Escala } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Logo, Suave, Subtitulo, Tela, Texto, Titulo } from '../../lib/ui';

const PROXIMAS = 3;

/** Destaque de uma escala de hoje, com confirmação direto no cartão se ainda estiver pendente. */
function CartaoDeHoje({ escala }: { escala: Escala }) {
  const { cores } = useTema();
  const acao = useAcaoDeEscala(escala.id);
  return (
    <Pressable onPress={() => router.push({ pathname: '/escala/[id]', params: { id: escala.id } })}>
      <Cartao style={{ borderColor: cores.primaria, borderWidth: 2 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Ionicons name="today-outline" size={22} color={cores.primaria} />
          <Subtitulo style={{ color: cores.primaria }}>Você serve hoje às {hora(escala.evento.data_inicio)}</Subtitulo>
        </View>
        <Texto>{escala.evento.nome}</Texto>
        <Suave>
          {escala.funcao} · {escala.equipe}
        </Suave>
        {escala.confirmada ? (
          <Etiqueta texto="Presença confirmada" cor={cores.confirmada} />
        ) : (
          <>
            <Erro erro={acao.error} />
            <Botao
              titulo="Confirmar presença"
              carregando={acao.isPending}
              aoTocar={() => acao.mutate({ tipo: 'confirmar' })}
            />
          </>
        )}
      </Cartao>
    </Pressable>
  );
}

export default function Inicio() {
  const { usuario } = useAuth();
  const home = useHome();
  const escalas = useEscalas();
  const dados = home.data;
  const semEquipe = dados?.em_equipe === false;

  // Escalas de hoje que ainda não terminaram vão para o destaque; as demais, para "Próximas escalas".
  const agora = new Date();
  const futuras = escalas.data ?? [];
  const deHoje = futuras.filter(
    (e) => isSameDay(new Date(e.evento.data_inicio), agora) && new Date(e.evento.data_fim) > agora,
  );
  const proximas = futuras
    .filter((e) => !deHoje.includes(e) && new Date(e.evento.data_fim) > agora)
    .slice(0, PROXIMAS);

  function atualizar() {
    void home.refetch();
    void escalas.refetch();
  }

  return (
    <Tela atualizando={home.isRefetching || escalas.isRefetching} aoAtualizar={atualizar}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <Logo tamanho={44} />
        <Titulo>Olá, {usuario?.first_name || usuario?.username}</Titulo>
      </View>
      <Estado consulta={home} />
      {dados && (
        <>
          {semEquipe && <AvisoSemEquipe />}

          {deHoje.map((escala) => (
            <CartaoDeHoje key={escala.id} escala={escala} />
          ))}

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

          <Subtitulo>Próximas escalas</Subtitulo>
          {escalas.isPending ? (
            <Estado consulta={escalas} />
          ) : proximas.length > 0 ? (
            <>
              {proximas.map((escala) => (
                <CartaoDeEscala key={escala.id} escala={escala} />
              ))}
              {futuras.length > deHoje.length + proximas.length && (
                <Pressable onPress={() => router.navigate('/escalas')} hitSlop={8} accessibilityRole="button">
                  <Suave style={{ textAlign: 'center' }}>Ver todas as escalas</Suave>
                </Pressable>
              )}
            </>
          ) : (
            <Suave>{deHoje.length ? 'Nenhuma outra escala marcada.' : 'Você não tem escalas futuras.'}</Suave>
          )}

          {!dados.tem_disponibilidade && !semEquipe && (
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
