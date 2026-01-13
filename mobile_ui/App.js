import React, { useState, useEffect } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  FlatList,
  ActivityIndicator,
  Alert,
  Modal,
  Image,
} from "react-native";

// API 基礎 URL：請改為本機區網 IP，供真機連線
const API_BASE_URL = "http://192.168.0.24:5000/api";

// ==================
// 登入屏幕
// ==================
const LoginScreen = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [registerData, setRegisterData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert("錯誤", "請輸入信箱和密碼");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (data.status === "success") {
        onLoginSuccess(data.user);
      } else {
        Alert.alert("登入失敗", data.message || "請檢查信箱和密碼");
      }
    } catch (error) {
      Alert.alert("錯誤", "無法連接到伺服器");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    if (
      !registerData.username ||
      !registerData.email ||
      !registerData.password
    ) {
      Alert.alert("錯誤", "請填寫所有欄位");
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      Alert.alert("錯誤", "密碼不一致");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: registerData.username,
          email: registerData.email,
          password: registerData.password,
        }),
      });

      const data = await response.json();
      if (data.status === "success") {
        Alert.alert("成功", "註冊成功，請登入");
        setShowRegister(false);
        setEmail(registerData.email);
        setPassword("");
        setRegisterData({
          username: "",
          email: "",
          password: "",
          confirmPassword: "",
        });
      } else {
        Alert.alert("註冊失敗", data.message || "請重試");
      }
    } catch (error) {
      Alert.alert("錯誤", "無法連接到伺服器");
    } finally {
      setIsLoading(false);
    }
  };

  if (showRegister) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView contentContainerStyle={styles.authContainer}>
          <Text style={styles.authTitle}>建立新帳戶</Text>

          <TextInput
            style={styles.input}
            placeholder="使用者名稱"
            value={registerData.username}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, username: text })
            }
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder="信箱"
            value={registerData.email}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, email: text })
            }
            keyboardType="email-address"
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder="密碼 (至少 6 個字元)"
            value={registerData.password}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, password: text })
            }
            secureTextEntry
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder="確認密碼"
            value={registerData.confirmPassword}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, confirmPassword: text })
            }
            secureTextEntry
            editable={!isLoading}
          />

          <TouchableOpacity
            style={styles.button}
            onPress={handleRegister}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>註冊</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity onPress={() => setShowRegister(false)}>
            <Text style={styles.link}>已有帳戶？點擊登入</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.authContainer}>
        <Text style={styles.authTitle}>演唱會通知助手</Text>
        <Text style={styles.subtitle}>登入你的帳戶</Text>

        <TextInput
          style={styles.input}
          placeholder="信箱"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          editable={!isLoading}
        />
        <TextInput
          style={styles.input}
          placeholder="密碼"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          editable={!isLoading}
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>登入</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setShowRegister(true)}>
          <Text style={styles.link}>還沒有帳戶？點擊註冊</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

// ==================
// 演唱會列表屏幕
// ==================
const ConcertListScreen = ({ user, onLogout }) => {
  const [concerts, setConcerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedConcert, setSelectedConcert] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [userFollows, setUserFollows] = useState([]);
  const [userReminders, setUserReminders] = useState({});
  const [currentTab, setCurrentTab] = useState("all"); // all, follows

  useEffect(() => {
    loadConcerts();
    loadFollows();
    loadReminders();
  }, []);

  const loadConcerts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/concerts`);
      const data = await response.json();
      if (data.status === "success") {
        setConcerts(data.concerts || []);
      }
    } catch (error) {
      console.error("載入演唱會失敗:", error);
      Alert.alert("錯誤", "無法載入演唱會列表");
    } finally {
      setIsLoading(false);
    }
  };

  const loadFollows = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/follows`);
      const data = await response.json();
      if (data.status === "success") {
        setUserFollows(data.concerts.map((c) => c.id) || []);
      }
    } catch (error) {
      console.error("載入關注失敗:", error);
    }
  };

  const loadReminders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/reminders`);
      const data = await response.json();
      if (data.status === "success") {
        setUserReminders(data.reminders || {});
      }
    } catch (error) {
      console.error("載入提醒失敗:", error);
    }
  };

  const toggleFollow = async (concertId) => {
    const isFollowing = userFollows.includes(concertId);
    const endpoint = isFollowing
      ? `${API_BASE_URL}/follows/${concertId}`
      : `${API_BASE_URL}/follows/${concertId}`;
    const method = isFollowing ? "DELETE" : "POST";

    try {
      const response = await fetch(endpoint, { method });
      const data = await response.json();

      if (data.status === "success") {
        if (isFollowing) {
          setUserFollows(userFollows.filter((id) => id !== concertId));
        } else {
          setUserFollows([...userFollows, concertId]);
        }
        Alert.alert("成功", isFollowing ? "已取消關注" : "已關注");
      }
    } catch (error) {
      Alert.alert("錯誤", "操作失敗");
    }
  };

  const toggleReminder = async (concertId) => {
    const hasReminder = userReminders[concertId];

    try {
      if (hasReminder) {
        await fetch(`${API_BASE_URL}/reminders/${concertId}`, {
          method: "DELETE",
        });
        const newReminders = { ...userReminders };
        delete newReminders[concertId];
        setUserReminders(newReminders);
        Alert.alert("成功", "已刪除提醒");
      } else {
        await fetch(`${API_BASE_URL}/reminders/${concertId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "on_sale" }),
        });
        setUserReminders({
          ...userReminders,
          [concertId]: { type: "on_sale", enabled: true },
        });
        Alert.alert("成功", "已設定提醒");
      }
    } catch (error) {
      Alert.alert("錯誤", "操作失敗");
    }
  };

  const filteredConcerts = concerts.filter(
    (concert) =>
      concert.演出藝人?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      concert.演出地點?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  let displayConcerts = filteredConcerts;
  if (currentTab === "follows") {
    displayConcerts = filteredConcerts.filter((c) => userFollows.includes(c.id));
  }

  const renderConcertItem = ({ item }) => {
    const isFollowed = userFollows.includes(item.id);
    const hasReminder = userReminders[item.id];

    return (
      <TouchableOpacity
        style={styles.concertCard}
        onPress={() => setSelectedConcert(item)}
      >
        <View style={styles.concertContent}>
          <Text style={styles.concertArtist} numberOfLines={2}>
            {item.演出藝人}
          </Text>
          <Text style={styles.concertInfo}>📅 {item.演出時間}</Text>
          <Text style={styles.concertInfo}>📍 {item.演出地點}</Text>
          <Text style={styles.concertSource}>{item.來源網站}</Text>
        </View>

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.smallButton, isFollowed && styles.followedButton]}
            onPress={() => toggleFollow(item.id)}
          >
            <Text style={styles.smallButtonText}>
              {isFollowed ? "★" : "☆"}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.smallButton, hasReminder && styles.reminderButton]}
            onPress={() => toggleReminder(item.id)}
          >
            <Text style={styles.smallButtonText}>
              {hasReminder ? "🔔" : "🔕"}
            </Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>歡迎, {user.username}! 👋</Text>
          <Text style={styles.subGreeting}>發現你的下一場演出</Text>
        </View>
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => {
            Alert.alert("確認", "確定要登出嗎?", [
              { text: "取消" },
              { text: "登出", onPress: onLogout },
            ]);
          }}
        >
          <Text style={styles.logoutText}>登出</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, currentTab === "all" && styles.activeTab]}
          onPress={() => setCurrentTab("all")}
        >
          <Text
            style={[
              styles.tabText,
              currentTab === "all" && styles.activeTabText,
            ]}
          >
            所有演唱會 ({concerts.length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, currentTab === "follows" && styles.activeTab]}
          onPress={() => setCurrentTab("follows")}
        >
          <Text
            style={[
              styles.tabText,
              currentTab === "follows" && styles.activeTabText,
            ]}
          >
            我的關注 ({userFollows.length})
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="搜尋演唱會..."
          placeholderTextColor="#999"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {isLoading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
        </View>
      ) : displayConcerts.length === 0 ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>
            {concerts.length === 0 ? "暫無演唱會資料" : "沒有符合的結果"}
          </Text>
        </View>
      ) : (
        <FlatList
          data={displayConcerts}
          renderItem={renderConcertItem}
          keyExtractor={(item, idx) => item.id || `concert-${idx}`}
          contentContainerStyle={styles.listContent}
        />
      )}

      {/* 詳細資訊 Modal */}
      {selectedConcert && (
        <Modal
          visible={!!selectedConcert}
          animationType="slide"
          transparent={true}
          onRequestClose={() => setSelectedConcert(null)}
        >
          <SafeAreaView style={styles.modalContainer}>
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setSelectedConcert(null)}>
                <Text style={styles.closeButton}>✕</Text>
              </TouchableOpacity>
              <Text style={styles.modalTitle}>演唱會詳情</Text>
              <View style={{ width: 30 }} />
            </View>

            <ScrollView contentContainerStyle={styles.modalContent}>
              <Text style={styles.detailTitle}>
                {selectedConcert.演出藝人}
              </Text>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>📅 時間</Text>
                <Text style={styles.detailValue}>
                  {selectedConcert.演出時間}
                </Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>📍 地點</Text>
                <Text style={styles.detailValue}>
                  {selectedConcert.演出地點}
                </Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>🌐 來源</Text>
                <Text style={styles.detailValue}>{selectedConcert.來源網站}</Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>🔗 購票連結</Text>
                <Text style={[styles.detailValue, styles.link]}>
                  {selectedConcert.網址}
                </Text>
              </View>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.largeButton}
                  onPress={() => toggleFollow(selectedConcert.id)}
                >
                  <Text style={styles.largeButtonText}>
                    {userFollows.includes(selectedConcert.id)
                      ? "取消關注 ★"
                      : "關注 ☆"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.largeButton}
                  onPress={() => toggleReminder(selectedConcert.id)}
                >
                  <Text style={styles.largeButtonText}>
                    {userReminders[selectedConcert.id]
                      ? "移除提醒 🔔"
                      : "設置提醒 🔕"}
                  </Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </SafeAreaView>
        </Modal>
      )}
    </SafeAreaView>
  );
};

// ==================
// 主應用
// ==================
export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUser(null);
  };

  return isLoggedIn && user ? (
    <ConcertListScreen user={user} onLogout={handleLogout} />
  ) : (
    <LoginScreen onLoginSuccess={handleLoginSuccess} />
  );
}

// ==================
// 樣式定義
// ==================
const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#0e1629",
  },

  // 認證屏幕
  authContainer: {
    padding: 20,
    justifyContent: "center",
    minHeight: "100%",
  },
  authTitle: {
    fontSize: 28,
    fontWeight: "800",
    color: "#f5f7ff",
    marginBottom: 8,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 16,
    color: "#c7d4ff",
    marginBottom: 30,
    textAlign: "center",
  },
  input: {
    backgroundColor: "#162b54",
    borderColor: "#24407a",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    color: "#f5f7ff",
    fontSize: 16,
  },
  button: {
    backgroundColor: "#007AFF",
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    marginTop: 8,
    marginBottom: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  link: {
    color: "#5ba3ff",
    textAlign: "center",
    fontSize: 14,
    textDecorationLine: "underline",
  },

  // 頭部
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#24407a",
  },
  greeting: {
    fontSize: 18,
    fontWeight: "700",
    color: "#f5f7ff",
  },
  subGreeting: {
    fontSize: 13,
    color: "#c7d4ff",
    marginTop: 2,
  },
  logoutButton: {
    backgroundColor: "#8b5cf6",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  logoutText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 13,
  },

  // 標籤頁
  tabContainer: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: "#24407a",
    paddingHorizontal: 16,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    borderBottomWidth: 3,
    borderBottomColor: "transparent",
    alignItems: "center",
  },
  activeTab: {
    borderBottomColor: "#007AFF",
  },
  tabText: {
    fontSize: 14,
    color: "#c7d4ff",
    fontWeight: "600",
  },
  activeTabText: {
    color: "#007AFF",
  },

  // 搜尋
  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  searchInput: {
    backgroundColor: "#162b54",
    borderColor: "#24407a",
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#f5f7ff",
    fontSize: 14,
  },

  // 演唱會卡片
  listContent: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  concertCard: {
    flexDirection: "row",
    backgroundColor: "#162b54",
    borderColor: "#24407a",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    justifyContent: "space-between",
    alignItems: "center",
  },
  concertContent: {
    flex: 1,
  },
  concertArtist: {
    fontSize: 15,
    fontWeight: "700",
    color: "#f5f7ff",
    marginBottom: 6,
  },
  concertInfo: {
    fontSize: 13,
    color: "#c7d4ff",
    marginBottom: 3,
  },
  concertSource: {
    fontSize: 11,
    color: "#8fa3c7",
    marginTop: 4,
  },
  actionButtons: {
    flexDirection: "row",
    gap: 8,
  },
  smallButton: {
    width: 40,
    height: 40,
    borderRadius: 8,
    backgroundColor: "#24407a",
    justifyContent: "center",
    alignItems: "center",
  },
  followedButton: {
    backgroundColor: "#fbbf24",
  },
  reminderButton: {
    backgroundColor: "#10b981",
  },
  smallButtonText: {
    fontSize: 18,
  },

  // Modal
  modalContainer: {
    flex: 1,
    backgroundColor: "#0e1629",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#24407a",
  },
  closeButton: {
    fontSize: 24,
    color: "#f5f7ff",
    fontWeight: "700",
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#f5f7ff",
  },
  modalContent: {
    padding: 16,
  },
  detailTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#f5f7ff",
    marginBottom: 20,
  },
  detailSection: {
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#24407a",
  },
  detailLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: "#8fa3c7",
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 15,
    color: "#e7edff",
    lineHeight: 20,
  },
  url: {
    color: "#5ba3ff",
  },
  modalActions: {
    marginTop: 20,
    gap: 12,
  },
  largeButton: {
    backgroundColor: "#007AFF",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  largeButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "700",
  },

  // 空白狀態
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  emptyText: {
    fontSize: 16,
    color: "#c7d4ff",
    fontWeight: "600",
  },
});
