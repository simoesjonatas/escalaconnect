import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router/js-tabs';
import { ComponentProps } from 'react';
import { ColorValue } from 'react-native';

import { useAuth } from '../../lib/auth';
import { useHome } from '../../lib/hooks';
import { useTema } from '../../lib/tema';

const icone =
  (nome: ComponentProps<typeof Ionicons>['name']) =>
  ({ color, size }: { color: ColorValue; size: number }) => <Ionicons name={nome} color={color} size={size} />;

export default function TabsLayout() {
  const { cores } = useTema();
  // Contador de escalas a confirmar na aba Escalas (some quando zera).
  const home = useHome().data;
  const pendentes = home?.escalas_pendentes ?? 0;
  // Aba Liderança só para quem lidera alguma equipe, com o total de pendências.
  const lider = useAuth().usuario?.lider ?? false;
  const pendenciasLider = home?.pendencias_lider ?? 0;
  const selo = { backgroundColor: cores.perigo, color: '#fff' };
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
      <Tabs.Screen name="index" options={{ title: 'Início', tabBarIcon: icone('home-outline') }} />
      <Tabs.Screen
        name="escalas"
        options={{
          title: 'Escalas',
          tabBarIcon: icone('clipboard-outline'),
          tabBarBadge: pendentes > 0 ? pendentes : undefined,
          tabBarBadgeStyle: selo,
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
          tabBarBadge: pendenciasLider > 0 ? pendenciasLider : undefined,
          tabBarBadgeStyle: selo,
        }}
      />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: icone('person-outline') }} />
    </Tabs>
  );
}
