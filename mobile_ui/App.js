import React from "react";
import { SafeAreaView, ScrollView, View, Text, TouchableOpacity, StyleSheet } from "react-native";

const Pill = ({ label }) => (
  <TouchableOpacity style={styles.pill}>
    <Text style={styles.pillText}>{label}</Text>
  </TouchableOpacity>
);

const CardButton = ({ label }) => (
  <TouchableOpacity style={styles.card}>
    <Text style={styles.cardText}>{label}</Text>
  </TouchableOpacity>
);

export default function App() {
  return (
    <SafeAreaView style={styles.safe}> 
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>找到你的下一場演出</Text>

        <View style={styles.rowWrap}>
          <Pill label="時間" />
          <Pill label="地點" />
          <Pill label="類型" />
          <Pill label="AI 推薦" />
        </View>

        <Text style={styles.section}>快速功能</Text>
        <View style={styles.rowWrap}>
          <CardButton label="興趣偏好" />
          <CardButton label="AI 助理" />
          <CardButton label="同類型推薦" />
          <CardButton label="數據分析" />
          <CardButton label="票券通知" />
          <CardButton label="搶票提醒" />
        </View>

        <Text style={styles.section}>探索</Text>
        <View style={styles.rowWrap}>
          <CardButton label="音樂季/樂團時間" />
          <CardButton label="活動評價討論" />
          <CardButton label="同好配對" />
          <CardButton label="票根收集" />
          <CardButton label="粉絲應援資訊" />
        </View>

        <Text style={styles.section}>周邊與出行</Text>
        <View style={styles.rowWrap}>
          <CardButton label="交通提醒" />
          <CardButton label="附近美食" />
          <CardButton label="附近飯店" />
          <CardButton label="手機/相機租借" />
        </View>

        <View style={styles.footer}>
          {["首頁", "探索", "票夾", "社群", "個人"].map((tab) => (
            <TouchableOpacity key={tab} style={styles.tab}>
              <Text style={styles.tabText}>{tab}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0e1629" },
  container: { padding: 16, gap: 12 },
  title: { fontSize: 22, fontWeight: "800", color: "#f5f7ff" },
  section: { fontSize: 16, fontWeight: "700", color: "#9bb5ff", marginTop: 8 },
  rowWrap: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: "#15294d",
    borderWidth: 1,
    borderColor: "#24407a",
  },
  pillText: { color: "#e7edff", fontWeight: "600", fontSize: 14 },
  card: {
    minWidth: "45%",
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 14,
    backgroundColor: "#162b54",
    borderWidth: 1,
    borderColor: "#24407a",
  },
  cardText: { color: "#e7edff", fontWeight: "700", fontSize: 14 },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: "#24407a",
    marginTop: 12,
  },
  tab: { padding: 8 },
  tabText: { color: "#c7d4ff", fontWeight: "600" },
});
