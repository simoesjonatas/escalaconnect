import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router/js-tabs';
import { ComponentProps } from 'react';
import { ColorValue } from 'react-native';

import { cores } from '../../lib/tema';

const icone =
  (nome: ComponentProps<typeof Ionicons>['name']) =>
  ({ color, size }: { color: ColorValue; size: number }) => <Ionicons name={nome} color={color} size={size} />;

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: cores.primaria, headerTitleStyle: { color: cores.texto } }}>
      <Tabs.Screen name="index" options={{ title: 'Início', tabBarIcon: icone('home-outline') }} />
      <Tabs.Screen name="escalas" options={{ title: 'Escalas', tabBarIcon: icone('clipboard-outline') }} />
      <Tabs.Screen name="calendario" options={{ title: 'Calendário', tabBarIcon: icone('calendar-outline') }} />
      <Tabs.Screen name="disponibilidade" options={{ title: 'Disponibilidade', tabBarIcon: icone('time-outline') }} />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: icone('person-outline') }} />
    </Tabs>
  );
}
