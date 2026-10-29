import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { ComponentProps, useEffect } from 'react';
import { ColorValue, Pressable, Text, View } from 'react-native';

import { useAuth } from '../../lib/auth';
import { useHome } from '../../lib/hooks';
import { sincronizarIcone } from '../../lib/push';
import { useTema } from '../../lib/tema';
import { contador } from '../../lib/ui';

const icone =
  (nome: ComponentProps<typeof Ionicons>['name']) =>
  ({ color, size }: { color: ColorValue; size: number }) => <Ionicons name={nome} color={color} size={size} />;

/** Sino do Início: abre a caixa de avisos e mostra quantos não foram lidos. */
function Sino({ naoLidos }: { naoLidos: number }) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={() => router.push('/avisos')}
      hitSlop={10}
      accessibilityRole="button"
      accessibilityLabel={naoLidos ? `Avisos, ${naoLidos} não lidos` : 'Avisos'}
      style={{ marginHorizontal: 16 }}>
      <Ionicons name={naoLidos ? 'notifications' : 'notifications-outline'} size={24} color={cores.texto} />
      {naoLidos > 0 && (
        <View
          style={{
            position: 'absolute',
            top: -6,
            right: -10,
            minWidth: 18,
            height: 18,
            borderRadius: 9,
            paddingHorizontal: 4,
            backgroundColor: cores.perigo,
            alignItems: 'center',
            justifyContent: 'center',
          }}>
          <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>{contador(naoLidos)}</Text>
        </View>
      )}
    </Pressable>
  );
}

export default function TabsLayout() {
  const { cores } = useTema();
  // Contador de escalas a confirmar na aba Escalas (some quando zera).
  const home = useHome().data;
  const pendentes = home?.escalas_pendentes ?? 0;
  // Aba Liderança só para quem lidera alguma equipe, com o total de pendências.
  const lider = useAuth().usuario?.lider ?? false;
  const pendenciasLider = home?.pendencias_lider ?? 0;
  const selo = { backgroundColor: cores.perigo, color: '#fff' };
  // O selo fica preso à largura do ícone da aba: "99+" precisa de largura própria para não virar "9…".
  const seloDe = (n: number) => (n > 99 ? { ...selo, width: 34, end: -14, fontSize: 10 } : selo);
  const naoLidos = home?.avisos_nao_lidos;
  // O número no ícone do app acompanha os avisos não lidos.
  useEffect(() => {
    if (naoLidos !== undefined) void sincronizarIcone(naoLidos);
  }, [naoLidos]);
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: cores.primaria,
        tabBarInactiveTintColor: cores.textoSuave,
        tabBarStyle: { backgroundColor: cores.cartao, borderTopColor: cores.borda },
        headerStyle: { backgroundColor: cores.cartao },
        headerTitleStyle: { color: cores.texto },
        headerShadowVisible: false,
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Início',
          tabBarIcon: icone('home-outline'),
          headerRight: () => <Sino naoLidos={naoLidos ?? 0} />,
        }}
      />
      <Tabs.Screen
        name="escalas"
        options={{
          title: 'Escalas',
          tabBarIcon: icone('clipboard-outline'),
          tabBarBadge: pendentes > 0 ? contador(pendentes) : undefined,
          tabBarBadgeStyle: seloDe(pendentes),
        }}
      />
      <Tabs.Screen name="calendario" options={{ title: 'Calendário', tabBarIcon: icone('calendar-outline') }} />
      <Tabs.Screen name="disponibilidade" options={{ title: 'Disponibilidade', tabBarIcon: icone('time-outline') }} />
      <Tabs.Screen
        name="lideranca"
        options={{
          title: 'Liderança',
          href: lider ? undefined : null,
          tabBarIcon: icone('people-outline'),
          tabBarBadge: pendenciasLider > 0 ? contador(pendenciasLider) : undefined,
          tabBarBadgeStyle: seloDe(pendenciasLider),
        }}
      />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: icone('person-outline') }} />
    </Tabs>
  );
}
