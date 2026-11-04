import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { createContext, ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { Pressable, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTema } from './tema';
import { Icone } from './ui';

/**
 * Navegação assistida: na primeira vez (e nas próximas aberturas, até a pessoa dispensar) o app
 * passa pelas abas explicando cada uma. "Sair" fecha só agora; "Não mostrar mais" e "Concluir"
 * guardam no aparelho que já viu. O Perfil tem "Ver o tour do app" para rever quando quiser.
 */

type Aba = 'index' | 'escalas' | 'calendario' | 'disponibilidade' | 'lideranca' | 'perfil';

type Passo = { aba: Aba; icone: Icone; titulo: string; texto: string };

const ROTA: Record<Aba, '/' | '/escalas' | '/calendario' | '/disponibilidade' | '/lideranca' | '/perfil'> = {
  index: '/',
  escalas: '/escalas',
  calendario: '/calendario',
  disponibilidade: '/disponibilidade',
  lideranca: '/lideranca',
  perfil: '/perfil',
};

const PASSOS: Passo[] = [
  {
    aba: 'index',
    icone: 'home-outline',
    titulo: 'Início',
    texto: 'Aqui aparece a sua próxima escala e o que precisa da sua atenção. O sino no alto guarda os avisos.',
  },
  {
    aba: 'escalas',
    icone: 'clipboard-outline',
    titulo: 'Escalas',
    texto: 'Todas as suas escalas. Toque em uma para confirmar presença, sinalizar um impedimento ou pedir troca.',
  },
  {
    aba: 'calendario',
    icone: 'calendar-outline',
    titulo: 'Calendário',
    texto: 'Os cultos e eventos do mês, com destaque nos dias em que você serve.',
  },
  {
    aba: 'disponibilidade',
    icone: 'time-outline',
    titulo: 'Disponibilidade',
    texto:
      'Marque os dias em que pode servir (dá para filtrar por dia da semana) e se ofereça para vagas em aberto da sua equipe.',
  },
  {
    aba: 'lideranca',
    icone: 'people-outline',
    titulo: 'Liderança',
    texto:
      'Só para líderes: pendências para aprovar, os cultos, as vagas e as ferramentas (criar eventos, PDF da escala e gerenciar a equipe).',
  },
  {
    aba: 'perfil',
    icone: 'person-outline',
    titulo: 'Perfil',
    texto:
      'Suas equipes, suas escalas na agenda do celular e a troca de senha. Para ver este tour de novo, use "Ver o tour do app" aqui.',
  },
];

const chave = (usuarioId: number) => `tour_visto_${usuarioId}`;

type Tour = { iniciar: () => void };

const ContextoDoTour = createContext<Tour>({ iniciar: () => {} });

/** Para o Perfil abrir o tour de novo. */
export const useTour = () => useContext(ContextoDoTour);

/** Envolve as abas: abre o tour sozinho enquanto não for dispensado neste aparelho e desenha o cartão. */
export function TourDoApp({
  usuarioId,
  lider,
  children,
}: {
  usuarioId: number | undefined;
  lider: boolean;
  children: ReactNode;
}) {
  const passos = PASSOS.filter((p) => lider || p.aba !== 'lideranca');
  const [passo, setPasso] = useState<number | null>(null);
  const verificado = useRef(false);

  // Uma vez por abertura do app: se ainda não dispensou neste aparelho, começa.
  useEffect(() => {
    if (!usuarioId || verificado.current) return;
    verificado.current = true;
    SecureStore.getItemAsync(chave(usuarioId))
      .then((visto) => {
        if (!visto) setPasso(0);
      })
      .catch(() => {});
  }, [usuarioId]);

  // Cada passo leva para a aba que ele explica.
  useEffect(() => {
    if (passo !== null) router.navigate(ROTA[passos[passo].aba]);
  }, [passo]); // eslint-disable-line react-hooks/exhaustive-deps

  function dispensar() {
    if (usuarioId) void SecureStore.setItemAsync(chave(usuarioId), '1').catch(() => {});
    setPasso(null);
  }

  return (
    <ContextoDoTour.Provider value={{ iniciar: () => setPasso(0) }}>
      {children}
      {passo !== null && (
        <Cartao
          passos={passos}
          lider={lider}
          indice={passo}
          aoVoltar={() => setPasso(passo - 1)}
          aoAvancar={() => (passo === passos.length - 1 ? dispensar() : setPasso(passo + 1))}
          aoSair={() => {
            setPasso(null);
            router.navigate('/');
          }}
          aoDispensar={() => {
            dispensar();
            router.navigate('/');
          }}
        />
      )}
    </ContextoDoTour.Provider>
  );
}

const ALTURA_DA_BARRA = 49; // barra de abas padrão, sem a área segura de baixo

function Cartao({
  passos,
  lider,
  indice,
  aoVoltar,
  aoAvancar,
  aoSair,
  aoDispensar,
}: {
  passos: Passo[];
  lider: boolean;
  indice: number;
  aoVoltar: () => void;
  aoAvancar: () => void;
  aoSair: () => void;
  aoDispensar: () => void;
}) {
  const { cores } = useTema();
  const { width } = useWindowDimensions();
  const { bottom } = useSafeAreaInsets();
  const passo = passos[indice];
  const ultimo = indice === passos.length - 1;

  // A seta aponta para o ícone da aba: as abas visíveis dividem a largura igualmente.
  const abas: Aba[] = [
    'index',
    'escalas',
    'calendario',
    'disponibilidade',
    ...(lider ? ['lideranca' as Aba] : []),
    'perfil',
  ];
  const largura = width / abas.length;
  const centro = (abas.indexOf(passo.aba) + 0.5) * largura;
  const barra = ALTURA_DA_BARRA + bottom;

  return (
    <View pointerEvents="box-none" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
      {/* Escurece a tela (sem tapar a barra de abas) e segura os toques enquanto o tour está aberto. */}
      <View
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: barra,
          backgroundColor: 'rgba(0,0,0,0.55)',
        }}
      />
      {/* Destaque em volta da aba explicada. */}
      <View
        pointerEvents="none"
        style={{
          position: 'absolute',
          bottom: bottom + 2,
          left: centro - largura / 2 + 4,
          width: largura - 8,
          height: ALTURA_DA_BARRA - 4,
          borderRadius: 12,
          borderWidth: 2,
          borderColor: cores.primaria,
        }}
      />

      <View
        accessibilityViewIsModal
        style={{
          position: 'absolute',
          left: 16,
          right: 16,
          bottom: barra + 14,
          backgroundColor: cores.cartao,
          borderRadius: 16,
          borderWidth: 1,
          borderColor: cores.borda,
          padding: 18,
          gap: 12,
          shadowColor: '#000',
          shadowOpacity: 0.3,
          shadowRadius: 16,
          elevation: 12,
        }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View
            style={{
              width: 36,
              height: 36,
              borderRadius: 18,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: cores.primaria,
            }}>
            <Ionicons name={passo.icone} size={20} color={cores.sobrePrimaria} />
          </View>
          <Text
            style={{
              flex: 1,
              fontSize: 18,
              fontWeight: '700',
              color: cores.texto,
            }}>
            {passo.titulo}
          </Text>
          <Pressable onPress={aoSair} hitSlop={10} accessibilityRole="button" accessibilityLabel="Sair do tour">
            <Ionicons name="close" size={22} color={cores.textoSuave} />
          </Pressable>
        </View>

        <Text style={{ fontSize: 15, lineHeight: 21, color: cores.texto }}>{passo.texto}</Text>

        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
          <View style={{ flexDirection: 'row', gap: 6 }} accessibilityLabel={`Passo ${indice + 1} de ${passos.length}`}>
            {passos.map((p, i) => (
              <View
                key={p.aba}
                style={{
                  width: i === indice ? 18 : 7,
                  height: 7,
                  borderRadius: 4,
                  backgroundColor: i === indice ? cores.primaria : cores.borda,
                }}
              />
            ))}
          </View>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            {indice > 0 && <BotaoDoTour texto="Voltar" aoTocar={aoVoltar} />}
            <BotaoDoTour texto={ultimo ? 'Concluir' : 'Próximo'} cheio aoTocar={aoAvancar} />
          </View>
        </View>

        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            borderTopWidth: 1,
            borderTopColor: cores.borda,
            paddingTop: 10,
          }}>
          <Pressable onPress={aoSair} hitSlop={8} accessibilityRole="button">
            <Text style={{ color: cores.textoSuave, fontWeight: '600' }}>Sair</Text>
          </Pressable>
          <Pressable onPress={aoDispensar} hitSlop={8} accessibilityRole="button">
            <Text style={{ color: cores.textoSuave, fontWeight: '600' }}>Não mostrar mais</Text>
          </Pressable>
        </View>
      </View>

      {/* Seta do cartão para a aba. */}
      <View
        pointerEvents="none"
        style={{
          position: 'absolute',
          bottom: barra + 6,
          left: Math.min(Math.max(centro - 9, 26), width - 44),
          width: 0,
          height: 0,
          borderLeftWidth: 9,
          borderRightWidth: 9,
          borderTopWidth: 9,
          borderLeftColor: 'transparent',
          borderRightColor: 'transparent',
          borderTopColor: cores.cartao,
        }}
      />
    </View>
  );
}

function BotaoDoTour({ texto, cheio, aoTocar }: { texto: string; cheio?: boolean; aoTocar: () => void }) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={aoTocar}
      accessibilityRole="button"
      style={({ pressed }) => ({
        paddingHorizontal: 16,
        paddingVertical: 9,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: cores.primaria,
        backgroundColor: cheio ? cores.primaria : 'transparent',
        opacity: pressed ? 0.7 : 1,
      })}>
      <Text
        style={{
          fontWeight: '700',
          color: cheio ? cores.sobrePrimaria : cores.primaria,
        }}>
        {texto}
      </Text>
    </Pressable>
  );
}
