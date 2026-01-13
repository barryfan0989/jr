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

// API 基礎 URL：真機使用區網 IP
const API_BASE_URL = "http://192.168.0.24:5000/api";

// ==================
// 多語言翻譯
// ==================
const translations = {
  "zh-TW": {
    loginTitle: "演唱會通知助手",
    loginSubtitle: "登入你的帳戶",
    registerTitle: "建立新帳戶",
    email: "信箱",
    password: "密碼",
    username: "使用者名稱",
    confirmPassword: "確認密碼",
    login: "登入",
    register: "註冊",
    logout: "登出",
    noAccount: "還沒有帳戶？點擊註冊",
    haveAccount: "已有帳戶？點擊登入",
    welcome: "歡迎",
    discoverNext: "發現你的下一場演出",
    allConcerts: "所有演唱會",
    myFollows: "我的關注",
    search: "搜尋演唱會...",
    noConcerts: "暫無演唱會資料",
    noResults: "沒有符合的結果",
    concertDetails: "演唱會詳情",
    time: "時間",
    location: "地點",
    source: "來源",
    ticketLink: "購票連結",
    follow: "關注",
    unfollow: "取消關注",
    reminder: "設置提醒",
    removeReminder: "移除提醒",
    reviews: "評價",
    addReview: "新增評價",
    rating: "評分",
    comment: "評論",
    submit: "提交",
    cancel: "取消",
    deleteConfirm: "確定要登出嗎?",
    confirmLogout: "登出",
    error: "錯誤",
    success: "成功",
    serverError: "無法連接到伺服器",
    daysRemaining: "天",
    hoursRemaining: "小時",
  },
  "en-US": {
    loginTitle: "Concert Notification Helper",
    loginSubtitle: "Sign in to your account",
    registerTitle: "Create New Account",
    email: "Email",
    password: "Password",
    username: "Username",
    confirmPassword: "Confirm Password",
    login: "Login",
    register: "Register",
    logout: "Logout",
    noAccount: "Don't have an account? Click to register",
    haveAccount: "Have an account? Click to login",
    welcome: "Welcome",
    discoverNext: "Discover your next concert",
    allConcerts: "All Concerts",
    myFollows: "My Follows",
    search: "Search concerts...",
    noConcerts: "No concerts available",
    noResults: "No matching results",
    concertDetails: "Concert Details",
    time: "Time",
    location: "Location",
    source: "Source",
    ticketLink: "Ticket Link",
    follow: "Follow",
    unfollow: "Unfollow",
    reminder: "Set Reminder",
    removeReminder: "Remove Reminder",
    reviews: "Reviews",
    addReview: "Add Review",
    rating: "Rating",
    comment: "Comment",
    submit: "Submit",
    cancel: "Cancel",
    deleteConfirm: "Are you sure you want to logout?",
    confirmLogout: "Logout",
    error: "Error",
    success: "Success",
    serverError: "Unable to connect to server",
    daysRemaining: "days",
    hoursRemaining: "hours",
  },
};

const getTranslation = (key, language) => {
  return translations[language]?.[key] || translations["zh-TW"][key] || key;
};

// ==================
// 倒計時函數
// ==================
const calculateCountdown = (concertDate) => {
  if (!concertDate) return null;
  
  try {
    // 處理各種日期格式：2026/01/16 或 2026-01-16
    const dateStr = concertDate.replace(/\//g, '-');
    const now = new Date();
    const concert = new Date(dateStr);
    
    // 檢查日期是否有效
    if (isNaN(concert.getTime())) {
      console.warn('Invalid date:', concertDate);
      return null;
    }
    
    const diff = concert - now;
    
    if (diff <= 0) return { status: "past" };
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    return { days, hours, status: "upcoming" };
  } catch (error) {
    console.error('Error calculating countdown:', error, concertDate);
    return null;
  }
};

// ==================
// 登入屏幕
// ==================
const LoginScreen = ({ onLoginSuccess, language, onLanguageChange }) => {
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
      Alert.alert(getTranslation("error", language), "請輸入信箱和密碼");
      return;
    }

    setIsLoading(true);
    try {
      console.log("Login attempt - Email:", email, "API URL:", API_BASE_URL);
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      console.log("Login response status:", response.status);
      const data = await response.json();
      console.log("Login response data:", data);
      
      if (data.status === "success") {
        onLoginSuccess(data.user);
      } else {
        Alert.alert(
          getTranslation("error", language),
          data.message || "請檢查信箱和密碼"
        );
      }
    } catch (error) {
      console.log("Login error:", error.message || error);
      Alert.alert(
        getTranslation("error", language), 
        `Error: ${error.message || "無法連接到伺服器"}`
      );
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
      Alert.alert(getTranslation("error", language), "請填寫所有欄位");
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      Alert.alert(getTranslation("error", language), "密碼不一致");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',
        body: JSON.stringify({
          username: registerData.username,
          email: registerData.email,
          password: registerData.password,
        }),
      });

      const data = await response.json();
      if (data.status === "success") {
        Alert.alert(getTranslation("success", language), "註冊成功，請登入");
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
      Alert.alert(getTranslation("error", language), getTranslation("serverError", language));
    } finally {
      setIsLoading(false);
    }
  };

  if (showRegister) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.languageToggle}>
          <TouchableOpacity onPress={() => onLanguageChange("zh-TW")}>
            <Text style={[styles.langButton, language === "zh-TW" && styles.langButtonActive]}>
              繁體中文
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => onLanguageChange("en-US")}>
            <Text style={[styles.langButton, language === "en-US" && styles.langButtonActive]}>
              English
            </Text>
          </TouchableOpacity>
        </View>
        <ScrollView contentContainerStyle={styles.authContainer}>
          <Text style={styles.authTitle}>
            {getTranslation("registerTitle", language)}
          </Text>

          <TextInput
            style={styles.input}
            placeholder={getTranslation("username", language)}
            value={registerData.username}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, username: text })
            }
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder={getTranslation("email", language)}
            value={registerData.email}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, email: text })
            }
            keyboardType="email-address"
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder={getTranslation("password", language) + " (至少 6 個字元)"}
            value={registerData.password}
            onChangeText={(text) =>
              setRegisterData({ ...registerData, password: text })
            }
            secureTextEntry
            editable={!isLoading}
          />
          <TextInput
            style={styles.input}
            placeholder={getTranslation("confirmPassword", language)}
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
              <Text style={styles.buttonText}>
                {getTranslation("register", language)}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity onPress={() => setShowRegister(false)}>
            <Text style={styles.link}>
              {getTranslation("haveAccount", language)}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.languageToggle}>
        <TouchableOpacity onPress={() => onLanguageChange("zh-TW")}>
          <Text style={[styles.langButton, language === "zh-TW" && styles.langButtonActive]}>
            繁體中文
          </Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => onLanguageChange("en-US")}>
          <Text style={[styles.langButton, language === "en-US" && styles.langButtonActive]}>
            English
          </Text>
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={styles.authContainer}>
        <Text style={styles.authTitle}>
          {getTranslation("loginTitle", language)}
        </Text>
        <Text style={styles.subtitle}>
          {getTranslation("loginSubtitle", language)}
        </Text>

        <TextInput
          style={styles.input}
          placeholder={getTranslation("email", language)}
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          editable={!isLoading}
        />
        <TextInput
          style={styles.input}
          placeholder={getTranslation("password", language)}
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
            <Text style={styles.buttonText}>
              {getTranslation("login", language)}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setShowRegister(true)}>
          <Text style={styles.link}>
            {getTranslation("noAccount", language)}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

// ==================
// 演唱會列表屏幕
// ==================
const ConcertListScreen = ({ user, onLogout, language, onLanguageChange }) => {
  const [concerts, setConcerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedConcert, setSelectedConcert] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [userFollows, setUserFollows] = useState([]);
  const [userReminders, setUserReminders] = useState({});
  const [currentTab, setCurrentTab] = useState("all");
  const [reviews, setReviews] = useState([]);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewData, setReviewData] = useState({ rating: 5, comment: "" });
  const [avgRating, setAvgRating] = useState(0);

  useEffect(() => {
    loadConcerts();
    loadFollows();
    loadReminders();
  }, []);

  const loadConcerts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/concerts`, { credentials: 'include' });
      const data = await response.json();
      if (data.status === "success") {
        setConcerts(data.concerts || []);
      }
    } catch (error) {
      console.error("載入演唱會失敗:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadFollows = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/follows`, { credentials: 'include' });
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
      const response = await fetch(`${API_BASE_URL}/reminders`, { credentials: 'include' });
      const data = await response.json();
      if (data.status === "success") {
        setUserReminders(data.reminders || {});
      }
    } catch (error) {
      console.error("載入提醒失敗:", error);
    }
  };

  const loadReviews = async (concertId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/reviews/${concertId}`, { credentials: 'include' });
      const data = await response.json();
      if (data.status === "success") {
        setReviews(data.reviews || []);
        setAvgRating(data.avg_rating || 0);
      }
    } catch (error) {
      console.error("載入評價失敗:", error);
    }
  };

  const toggleFollow = async (concertId) => {
    const isFollowing = userFollows.includes(concertId);
    const method = isFollowing ? "DELETE" : "POST";

    try {
      const response = await fetch(`${API_BASE_URL}/follows/${concertId}`, {
        method: method,
        credentials: 'include',
        headers: { 'X-User-Id': user.user_id },
      });
      const data = await response.json();

      if (data.status === "success") {
        if (isFollowing) {
          setUserFollows(userFollows.filter((id) => id !== concertId));
        } else {
          setUserFollows([...userFollows, concertId]);
        }
      }
    } catch (error) {
      Alert.alert(getTranslation("error", language), "操作失敗");
    }
  };

  const toggleReminder = async (concertId) => {
    const hasReminder = userReminders[concertId];

    try {
      if (hasReminder) {
        await fetch(`${API_BASE_URL}/reminders/${concertId}`, {
          method: "DELETE",
          credentials: 'include',
          headers: { 'X-User-Id': user.user_id },
        });
        const newReminders = { ...userReminders };
        delete newReminders[concertId];
        setUserReminders(newReminders);
      } else {
        await fetch(`${API_BASE_URL}/reminders/${concertId}`, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            'X-User-Id': user.user_id 
          },
          credentials: 'include',
          body: JSON.stringify({ type: "on_sale" }),
        });
        setUserReminders({
          ...userReminders,
          [concertId]: { type: "on_sale", enabled: true },
        });
      }
    } catch (error) {
      Alert.alert(getTranslation("error", language), "操作失敗");
    }
  };

  const submitReview = async () => {
    if (!reviewData.comment.trim()) {
      Alert.alert(getTranslation("error", language), "請輸入評論");
      return;
    }

    try {
      console.log('Submitting review for concert:', selectedConcert.id);
      const response = await fetch(
        `${API_BASE_URL}/reviews/${selectedConcert.id}`,
        {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            'X-User-Id': user.user_id 
          },
          credentials: 'include',
          body: JSON.stringify({
            rating: reviewData.rating,
            comment: reviewData.comment,
          }),
        }
      );

      console.log('Review response status:', response.status);
      const data = await response.json();
      console.log('Review response data:', data);
      
      if (data.status === "success") {
        Alert.alert(getTranslation("success", language), "評價已提交");
        setReviewData({ rating: 5, comment: "" });
        setShowReviewModal(false);
        loadReviews(selectedConcert.id);
      } else {
        Alert.alert(getTranslation("error", language), data.message || "評價提交失敗");
      }
    } catch (error) {
      console.error('提交評價錯誤:', error);
      Alert.alert(getTranslation("error", language), `網路錯誤: ${error.message}`);
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
    const countdown = calculateCountdown(item.演出時間);

    return (
      <TouchableOpacity
        style={styles.concertCard}
        onPress={() => {
          setSelectedConcert(item);
          loadReviews(item.id);
          setShowReviewModal(false);
        }}
      >
        <View style={styles.concertContent}>
          <Text style={styles.concertArtist} numberOfLines={2}>
            {item.演出藝人}
          </Text>
          <Text style={styles.concertInfo}>📅 {item.演出時間}</Text>
          <Text style={styles.concertInfo}>📍 {item.演出地點}</Text>

          {countdown && countdown.status === "upcoming" && (
            <Text style={styles.countdown}>
              ⏱️ {countdown.days}天 {countdown.hours}小時
            </Text>
          )}

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
          <Text style={styles.greeting}>
            {getTranslation("welcome", language)}, {user.username}! 👋
          </Text>
          <Text style={styles.subGreeting}>
            {getTranslation("discoverNext", language)}
          </Text>
        </View>
        <View style={styles.headerButtons}>
          <TouchableOpacity
            style={styles.langToggle}
            onPress={() =>
              onLanguageChange(language === "zh-TW" ? "en-US" : "zh-TW")
            }
          >
            <Text style={styles.langToggleText}>
              {language === "zh-TW" ? "EN" : "繁"}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.logoutButton}
            onPress={() => {
              Alert.alert(
                getTranslation("deleteConfirm", language),
                "",
                [
                  { text: getTranslation("cancel", language) },
                  {
                    text: getTranslation("confirmLogout", language),
                    onPress: onLogout,
                  },
                ]
              );
            }}
          >
            <Text style={styles.logoutText}>
              {getTranslation("logout", language)}
            </Text>
          </TouchableOpacity>
        </View>
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
            {getTranslation("allConcerts", language)} ({concerts.length})
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
            {getTranslation("myFollows", language)} ({userFollows.length})
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder={getTranslation("search", language)}
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
            {concerts.length === 0
              ? getTranslation("noConcerts", language)
              : getTranslation("noResults", language)}
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
              <Text style={styles.modalTitle}>
                {getTranslation("concertDetails", language)}
              </Text>
              <View style={{ width: 30 }} />
            </View>

            <ScrollView contentContainerStyle={styles.modalContent}>
              <Text style={styles.detailTitle}>
                {selectedConcert.演出藝人}
              </Text>

              {calculateCountdown(selectedConcert.演出時間) &&
                calculateCountdown(selectedConcert.演出時間).status === "upcoming" && (
                  <View style={styles.countdownBox}>
                    <Text style={styles.countdownText}>
                      ⏱️ {calculateCountdown(selectedConcert.演出時間).days}
                      {getTranslation("daysRemaining", language)} {calculateCountdown(selectedConcert.演出時間).hours}
                      {getTranslation("hoursRemaining", language)}
                    </Text>
                  </View>
                )}

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>📅 {getTranslation("time", language)}</Text>
                <Text style={styles.detailValue}>
                  {selectedConcert.演出時間}
                </Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>📍 {getTranslation("location", language)}</Text>
                <Text style={styles.detailValue}>
                  {selectedConcert.演出地點}
                </Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>🌐 {getTranslation("source", language)}</Text>
                <Text style={styles.detailValue}>{selectedConcert.來源網站}</Text>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>🔗 {getTranslation("ticketLink", language)}</Text>
                <Text style={[styles.detailValue, styles.link]}>
                  {selectedConcert.網址}
                </Text>
              </View>

              <View style={styles.reviewSection}>
                <View style={styles.reviewHeader}>
                  <Text style={styles.reviewTitle}>
                    {getTranslation("reviews", language)}
                  </Text>
                  <Text style={styles.avgRating}>
                    ⭐ {avgRating.toFixed(1)}
                  </Text>
                </View>

                {reviews.length > 0 ? (
                  reviews.slice(0, 3).map((review) => (
                    <View key={review.id} style={styles.reviewItem}>
                      <View style={styles.reviewMeta}>
                        <Text style={styles.reviewUser}>{review.username}</Text>
                        <Text style={styles.reviewRating}>
                          {"⭐".repeat(review.rating)}
                        </Text>
                      </View>
                      <Text style={styles.reviewComment}>{review.comment}</Text>
                    </View>
                  ))
                ) : (
                  <Text style={styles.noReviewText}>暫無評價</Text>
                )}

                <TouchableOpacity
                  style={styles.addReviewButton}
                  onPress={() => setShowReviewModal(true)}
                >
                  <Text style={styles.addReviewButtonText}>
                    {getTranslation("addReview", language)}
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.largeButton}
                  onPress={() => toggleFollow(selectedConcert.id)}
                >
                  <Text style={styles.largeButtonText}>
                    {userFollows.includes(selectedConcert.id)
                      ? getTranslation("unfollow", language) + " ★"
                      : getTranslation("follow", language) + " ☆"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.largeButton}
                  onPress={() => toggleReminder(selectedConcert.id)}
                >
                  <Text style={styles.largeButtonText}>
                    {userReminders[selectedConcert.id]
                      ? getTranslation("removeReminder", language) + " 🔔"
                      : getTranslation("reminder", language) + " 🔕"}
                  </Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </SafeAreaView>
        </Modal>
      )}

      <Modal
        visible={showReviewModal && !!selectedConcert}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowReviewModal(false)}
      >
        <SafeAreaView style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setShowReviewModal(false)}>
              <Text style={styles.closeButton}>✕</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>
              {getTranslation("addReview", language)}
            </Text>
            <View style={{ width: 30 }} />
          </View>

          <ScrollView contentContainerStyle={styles.modalContent}>
            <Text style={styles.detailTitle}>
              {selectedConcert?.演出藝人}
            </Text>

            <View style={styles.ratingContainer}>
              <Text style={styles.ratingLabel}>
                {getTranslation("rating", language)}
              </Text>
              <View style={styles.ratingButtons}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <TouchableOpacity
                    key={star}
                    style={[
                      styles.ratingButton,
                      reviewData.rating >= star &&
                        styles.ratingButtonActive,
                    ]}
                    onPress={() =>
                      setReviewData({ ...reviewData, rating: star })
                    }
                  >
                    <Text style={styles.ratingButtonText}>⭐</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <View style={styles.commentContainer}>
              <Text style={styles.commentLabel}>
                {getTranslation("comment", language)}
              </Text>
              <TextInput
                style={styles.commentInput}
                placeholder={getTranslation("comment", language)}
                placeholderTextColor="#999"
                value={reviewData.comment}
                onChangeText={(text) =>
                  setReviewData({
                    ...reviewData,
                    comment: text.slice(0, 500),
                  })
                }
                multiline
                numberOfLines={5}
              />
              <Text style={styles.charCount}>
                {reviewData.comment.length}/500
              </Text>
            </View>

            <TouchableOpacity
              style={styles.submitButton}
              onPress={submitReview}
            >
              <Text style={styles.submitButtonText}>
                {getTranslation("submit", language)}
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
};

// ==================
// 主應用
// ==================
export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [language, setLanguage] = useState("zh-TW");

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUser(null);
  };

  const handleLanguageChange = (newLanguage) => {
    setLanguage(newLanguage);
  };

  return isLoggedIn && user ? (
    <ConcertListScreen
      user={user}
      onLogout={handleLogout}
      language={language}
      onLanguageChange={handleLanguageChange}
    />
  ) : (
    <LoginScreen
      onLoginSuccess={handleLoginSuccess}
      language={language}
      onLanguageChange={handleLanguageChange}
    />
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

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#24407a",
  },
  headerButtons: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
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
  langToggle: {
    backgroundColor: "#24407a",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
  },
  langToggleText: {
    color: "#f5f7ff",
    fontSize: 12,
    fontWeight: "700",
  },
  languageToggle: {
    flexDirection: "row",
    justifyContent: "flex-end",
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  langButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: "#24407a",
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "transparent",
  },
  langButtonActive: {
    backgroundColor: "#007AFF",
    borderColor: "#0056cc",
  },

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
  countdown: {
    fontSize: 12,
    color: "#ff6b6b",
    fontWeight: "700",
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
  countdownBox: {
    backgroundColor: "#ff6b6b20",
    borderLeftWidth: 3,
    borderLeftColor: "#ff6b6b",
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 20,
    borderRadius: 6,
  },
  countdownText: {
    fontSize: 14,
    color: "#ff6b6b",
    fontWeight: "700",
  },

  reviewSection: {
    marginTop: 20,
    marginBottom: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "#24407a",
  },
  reviewHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  reviewTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#f5f7ff",
  },
  avgRating: {
    fontSize: 18,
    fontWeight: "700",
    color: "#fbbf24",
  },
  reviewItem: {
    backgroundColor: "#24407a40",
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  reviewMeta: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  reviewUser: {
    fontSize: 13,
    fontWeight: "700",
    color: "#c7d4ff",
  },
  reviewRating: {
    fontSize: 13,
  },
  reviewComment: {
    fontSize: 13,
    color: "#e7edff",
    lineHeight: 18,
  },
  noReviewText: {
    fontSize: 13,
    color: "#8fa3c7",
    fontStyle: "italic",
  },
  addReviewButton: {
    backgroundColor: "#10b981",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
    marginTop: 12,
  },
  addReviewButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "700",
  },

  ratingContainer: {
    marginBottom: 20,
  },
  ratingLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: "#8fa3c7",
    marginBottom: 10,
  },
  ratingButtons: {
    flexDirection: "row",
    gap: 10,
    justifyContent: "center",
  },
  ratingButton: {
    width: 50,
    height: 50,
    borderRadius: 10,
    backgroundColor: "#24407a",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: "transparent",
  },
  ratingButtonActive: {
    backgroundColor: "#fbbf24",
    borderColor: "#f59e0b",
  },
  ratingButtonText: {
    fontSize: 24,
  },

  commentContainer: {
    marginBottom: 20,
  },
  commentLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: "#8fa3c7",
    marginBottom: 10,
  },
  commentInput: {
    backgroundColor: "#162b54",
    borderColor: "#24407a",
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    color: "#f5f7ff",
    fontSize: 14,
    textAlignVertical: "top",
  },
  charCount: {
    fontSize: 12,
    color: "#8fa3c7",
    textAlign: "right",
    marginTop: 6,
  },
  submitButton: {
    backgroundColor: "#007AFF",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 12,
  },
  submitButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
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
