import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [systemStatus, setSystemStatus] = useState(null);
  const [leagues, setLeagues] = useState([]);
  const [todayPredictions, setTodayPredictions] = useState([]);
  const [allPredictions, setAllPredictions] = useState([]);
  const [upcomingMatches, setUpcomingMatches] = useState([]);
  const [recentMatches, setRecentMatches] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [selectedLeague, setSelectedLeague] = useState(null);
  const [leagueStats, setLeagueStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Sistem durumunu kontrol et
      const statusResponse = await axios.get(`${API}/system/status`);
      setSystemStatus(statusResponse.data);
      
      // Ligleri getir
      const leaguesResponse = await axios.get(`${API}/leagues`);
      setLeagues(leaguesResponse.data.leagues);
      
      // Bugünkü tahminleri getir
      const predictionsResponse = await axios.get(`${API}/predictions/today`);
      setTodayPredictions(predictionsResponse.data.predictions);
      
      // Tüm tahminleri getir
      const allPredictionsResponse = await axios.get(`${API}/predictions/all?limit=20`);
      setAllPredictions(allPredictionsResponse.data.predictions);
      
      // Yaklaşan maçları getir
      const matchesResponse = await axios.get(`${API}/matches/upcoming`);
      setUpcomingMatches(matchesResponse.data.matches);
      
      // Son maçları getir
      const recentMatchesResponse = await axios.get(`${API}/matches/recent`);
      setRecentMatches(recentMatchesResponse.data.matches);
      
      // Performans istatistiklerini getir
      const performanceResponse = await axios.get(`${API}/stats/performance`);
      setPerformance(performanceResponse.data);
      
    } catch (error) {
      console.error('Veri yükleme hatası:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadInitialData();
    setRefreshing(false);
  };

  const generateDemoData = async () => {
    try {
      await axios.post(`${API}/data/generate-demo`);
      alert('Demo verisi oluşturma işlemi başlatıldı! Birkaç saniye sonra sayfayı yenileyin.');
    } catch (error) {
      console.error('Demo veri oluşturma hatası:', error);
      alert('Demo veri oluşturma işlemi başlatılamadı!');
    }
  };

  const triggerScraper = async () => {
    try {
      await axios.post(`${API}/scraper/run`);
      alert('Gelişmiş veri toplama işlemi başlatıldı!');
    } catch (error) {
      console.error('Scraper başlatılamadı:', error);
      alert('Veri toplama işlemi başlatılamadı!');
    }
  };

  const generatePredictions = async () => {
    try {
      await axios.post(`${API}/prediction/generate`);
      alert('Gelişmiş tahmin üretme işlemi başlatıldı!');
    } catch (error) {
      console.error('Tahmin üretme başlatılamadı:', error);
      alert('Tahmin üretme işlemi başlatılamadı!');
    }
  };

  const loadLeagueStats = async (leagueId) => {
    try {
      const response = await axios.get(`${API}/stats/league/${leagueId}`);
      setLeagueStats(response.data);
      setSelectedLeague(leagueId);
    } catch (error) {
      console.error('Lig istatistikleri yüklenemedi:', error);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return 'text-green-400';
    if (confidence >= 70) return 'text-yellow-400';
    if (confidence >= 60) return 'text-orange-400';
    return 'text-red-400';
  };

  const getConfidenceBg = (confidence) => {
    if (confidence >= 80) return 'bg-green-600/20 border-green-500/30';
    if (confidence >= 70) return 'bg-yellow-600/20 border-yellow-500/30';
    if (confidence >= 60) return 'bg-orange-600/20 border-orange-500/30';
    return 'bg-red-600/20 border-red-500/30';
  };

  const getBetTypeIcon = (betType) => {
    switch (betType) {
      case '1X2': return '🎯';
      case 'O/U2.5': return '⚽';
      case 'BTTS': return '🔄';
      default: return '📊';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-yellow-400 mx-auto"></div>
          <p className="text-white mt-4 text-xl">Gelişmiş sistem yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900">
      {/* Enhanced Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-3xl">🎯</div>
              <div>
                <h1 className="text-2xl font-bold text-white">Gelişmiş Bahis Tahmin Sistemi</h1>
                <p className="text-blue-300 text-sm">58+ Ligden AI Destekli Gelişmiş Tahminler v2.0</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={refreshData}
                className={`bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors ${refreshing ? 'opacity-50' : ''}`}
                disabled={refreshing}
              >
                {refreshing ? '🔄' : '🔄'} Yenile
              </button>
              <button
                onClick={generateDemoData}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                📊 Demo Veri
              </button>
              <button
                onClick={triggerScraper}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                🔄 Veri Topla
              </button>
              <button
                onClick={generatePredictions}
                className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                🧠 Tahmin Üret
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Enhanced Status Cards */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Sistem Durumu</p>
                <p className="text-white text-xl font-bold">
                  {systemStatus?.status === 'healthy' ? '✅ v2.0 Aktif' : '❌ Hata'}
                </p>
                <p className="text-gray-400 text-xs mt-1">
                  {systemStatus?.collections?.teams || 0} takım yüklü
                </p>
              </div>
              <div className="text-3xl">🖥️</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Aktif Ligler</p>
                <p className="text-white text-xl font-bold">{systemStatus?.collections?.leagues?.active || 0}</p>
                <p className="text-gray-400 text-xs mt-1">
                  {systemStatus?.collections?.matches?.total || 0} toplam maç
                </p>
              </div>
              <div className="text-3xl">🏆</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Tahmin Sayısı</p>
                <p className="text-white text-xl font-bold">{systemStatus?.collections?.predictions || 0}</p>
                <p className="text-gray-400 text-xs mt-1">
                  {systemStatus?.recent_activity?.predictions_24h || 0} son 24 saat
                </p>
              </div>
              <div className="text-3xl">📈</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Başarı Oranı</p>
                <p className="text-white text-xl font-bold">
                  {performance?.overall_performance?.last_30_days?.accuracy_percentage || 0}%
                </p>
                <p className="text-gray-400 text-xs mt-1">
                  Son 30 gün ortalama
                </p>
              </div>
              <div className="text-3xl">🎯</div>
            </div>
          </div>
        </div>

        {/* Enhanced Tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'dashboard'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            📊 Dashboard
          </button>
          <button
            onClick={() => setActiveTab('predictions')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'predictions'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            🎯 Tahminler
          </button>
          <button
            onClick={() => setActiveTab('matches')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'matches'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            ⚽ Maçlar
          </button>
          <button
            onClick={() => setActiveTab('leagues')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'leagues'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            🏆 Ligler
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'analytics'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            📈 Analitik
          </button>
        </div>

        {/* Enhanced Content */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
          {activeTab === 'dashboard' && (
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-6">📊 Gelişmiş Dashboard</h2>
              
              {/* Today's Best Predictions */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-white mb-4">🔥 Bugünün En İyi Tahminleri</h3>
                {todayPredictions.length === 0 ? (
                  <div className="text-center py-6">
                    <p className="text-blue-300">Bugün için tahmin bulunmuyor.</p>
                    <button 
                      onClick={generateDemoData}
                      className="mt-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      Demo Veri Oluştur
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {todayPredictions.slice(0, 6).map((prediction, index) => (
                      <div key={index} className={`rounded-lg p-4 border ${getConfidenceBg(prediction.confidence)}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-2xl">{getBetTypeIcon(prediction.bet_type)}</span>
                          <span className={`font-bold ${getConfidenceColor(prediction.confidence)}`}>
                            %{prediction.confidence}
                          </span>
                        </div>
                        <div className="text-white">
                          <p className="font-medium text-sm">
                            {prediction.home_team_name} vs {prediction.away_team_name}
                          </p>
                          <p className="text-blue-300 text-xs">{prediction.league_name}</p>
                          <div className="mt-2 flex items-center justify-between">
                            <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs">
                              {prediction.bet_type}
                            </span>
                            <span className="text-yellow-400 font-bold text-sm">
                              {prediction.predicted_outcome}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Upcoming Matches Preview */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-white mb-4">⏰ Yaklaşan Önemli Maçlar</h3>
                {upcomingMatches.length === 0 ? (
                  <p className="text-blue-300 text-center py-4">Yaklaşan maç bulunmuyor.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {upcomingMatches.slice(0, 4).map((match, index) => (
                      <div key={index} className="bg-white/5 rounded-lg p-4 border border-white/10">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-white font-medium">
                              {match.home_team_name} vs {match.away_team_name}
                            </p>
                            <p className="text-blue-300 text-sm">{match.league_name}</p>
                            <p className="text-gray-400 text-xs">
                              {formatDate(match.match_date)} - {formatTime(match.match_date)}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-green-400 text-sm">
                              {match.predictions?.length || 0} tahmin
                            </div>
                            {match.odds_1x2 && (
                              <div className="text-xs text-gray-400 mt-1">
                                1:{match.odds_1x2['1']} X:{match.odds_1x2['X']} 2:{match.odds_1x2['2']}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Results */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">📋 Son Sonuçlar</h3>
                {recentMatches.length === 0 ? (
                  <p className="text-blue-300 text-center py-4">Son maç sonucu bulunmuyor.</p>
                ) : (
                  <div className="space-y-3">
                    {recentMatches.slice(0, 5).map((match, index) => (
                      <div key={index} className="bg-white/5 rounded-lg p-3 border border-white/10">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <div className="text-center">
                              <p className="text-white text-sm font-medium">{match.home_team_name}</p>
                              <p className="text-blue-300 text-xs">vs</p>
                              <p className="text-white text-sm font-medium">{match.away_team_name}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-yellow-400 text-lg font-bold">
                                {match.home_score} - {match.away_score}
                              </p>
                              <p className="text-gray-400 text-xs">{formatDate(match.match_date)}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-blue-300 text-sm">{match.league_name}</p>
                            {match.home_xg && match.away_xg && (
                              <p className="text-gray-400 text-xs">
                                xG: {match.home_xg} - {match.away_xg}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'predictions' && (
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">🎯 Tüm Tahminler</h2>
              
              {allPredictions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-blue-300 text-lg">Henüz tahmin bulunmuyor.</p>
                  <p className="text-gray-400 mt-2">Demo veri oluşturarak tahminleri görebilirsiniz.</p>
                  <button 
                    onClick={generateDemoData}
                    className="mt-4 bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors"
                  >
                    Demo Veri Oluştur
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {allPredictions.map((prediction, index) => (
                    <div key={index} className={`rounded-lg p-4 border ${getConfidenceBg(prediction.confidence)}`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{getBetTypeIcon(prediction.bet_type)}</span>
                          <div>
                            <p className="text-white font-medium">
                              {prediction.home_team_name} vs {prediction.away_team_name}
                            </p>
                            <p className="text-blue-300 text-sm">{prediction.league_name}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`font-bold text-lg ${getConfidenceColor(prediction.confidence)}`}>
                            %{prediction.confidence}
                          </p>
                          <p className="text-gray-400 text-sm">Güven</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm">
                            {prediction.bet_type}
                          </span>
                          <span className="text-yellow-400 font-bold">
                            {prediction.predicted_outcome}
                          </span>
                          <span className="text-gray-400 text-sm">
                            Olasılık: %{Math.round(prediction.probability * 100)}
                          </span>
                        </div>
                        <div className="text-right">
                          <p className="text-gray-400 text-sm">
                            Model: {prediction.model_version}
                          </p>
                          {prediction.match_time && (
                            <p className="text-blue-300 text-sm">
                              {formatDate(prediction.match_time)} {formatTime(prediction.match_time)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'matches' && (
            <div className="p-6">
              <div className="flex space-x-4 mb-6">
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg">
                  ⏰ Yaklaşan Maçlar ({upcomingMatches.length})
                </button>
                <button className="bg-gray-600 text-white px-4 py-2 rounded-lg">
                  📋 Son Maçlar ({recentMatches.length})
                </button>
              </div>

              <h2 className="text-xl font-bold text-white mb-4">⚽ Maç Programı</h2>
              
              {upcomingMatches.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-blue-300 text-lg">Yaklaşan maç bulunmuyor.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {upcomingMatches.map((match, index) => (
                    <div key={index} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-6">
                          <div className="text-center min-w-[120px]">
                            <p className="text-white font-bold">{match.home_team_name}</p>
                            <p className="text-blue-300 text-sm">vs</p>
                            <p className="text-white font-bold">{match.away_team_name}</p>
                          </div>
                          
                          <div className="text-center">
                            <p className="text-blue-300 text-sm">{match.league_name}</p>
                            <p className="text-white font-medium">
                              {formatDate(match.match_date)}
                            </p>
                            <p className="text-gray-400 text-sm">
                              {formatTime(match.match_date)}
                            </p>
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className="flex space-x-4 mb-2">
                            {match.odds_1x2 && (
                              <div className="text-center">
                                <p className="text-gray-400 text-xs">1X2</p>
                                <p className="text-white text-sm">
                                  {match.odds_1x2['1']} | {match.odds_1x2['X']} | {match.odds_1x2['2']}
                                </p>
                              </div>
                            )}
                          </div>
                          <div className="flex space-x-2">
                            {match.predictions?.map((pred, pidx) => (
                              <span key={pidx} className="bg-green-600 text-white px-2 py-1 rounded text-xs">
                                {pred.bet_type}: {pred.predicted_outcome}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'leagues' && (
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">🏆 Desteklenen Ligler</h2>
              
              {leagues.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-blue-300 text-lg">Henüz lig verisi yüklenmemiş.</p>
                  <p className="text-gray-400 mt-2">Veri toplama işlemini başlatarak ligleri yükleyebilirsiniz.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {leagues.map((league, index) => (
                    <div 
                      key={index} 
                      className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer"
                      onClick={() => loadLeagueStats(league.id)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-white font-bold">{league.name}</h3>
                        <span className="text-blue-400 text-sm">{league.country}</span>
                      </div>
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-gray-400 text-sm">Sezon: {league.season}</p>
                        <span className="bg-green-600 text-white px-2 py-1 rounded text-xs">
                          {league.active ? 'Aktif' : 'Pasif'}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="text-center">
                          <p className="text-gray-400">Takım</p>
                          <p className="text-white font-bold">{league.statistics?.teams || 0}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-gray-400">Maç</p>
                          <p className="text-white font-bold">{league.statistics?.matches || 0}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-gray-400">Tahmin</p>
                          <p className="text-white font-bold">{league.statistics?.predictions || 0}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* League Details Modal */}
              {selectedLeague && leagueStats && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-white text-lg font-bold">{leagueStats.league.name}</h3>
                      <button
                        onClick={() => setSelectedLeague(null)}
                        className="text-gray-400 hover:text-white"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Ülke:</span>
                        <span className="text-white">{leagueStats.league.country}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Takım Sayısı:</span>
                        <span className="text-white">{leagueStats.statistics.teams}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Toplam Maç:</span>
                        <span className="text-white">{leagueStats.statistics.total_matches}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Tamamlanan:</span>
                        <span className="text-white">{leagueStats.statistics.finished_matches}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Tahmin Sayısı:</span>
                        <span className="text-white">{leagueStats.statistics.predictions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Ortalama Gol:</span>
                        <span className="text-white">{leagueStats.statistics.avg_goals_per_match}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-6">📈 Gelişmiş Analitik</h2>
              
              {performance ? (
                <div className="space-y-6">
                  {/* Overall Performance */}
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h3 className="text-lg font-semibold text-white mb-4">🎯 Genel Performans</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="text-center">
                        <p className="text-gray-400 text-sm">Son 30 Gün</p>
                        <p className="text-white text-2xl font-bold">
                          %{performance.overall_performance.last_30_days.accuracy_percentage}
                        </p>
                        <p className="text-blue-300 text-sm">
                          {performance.overall_performance.last_30_days.correct_predictions} / {performance.overall_performance.last_30_days.total_predictions} doğru
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400 text-sm">Son 7 Gün</p>
                        <p className="text-white text-2xl font-bold">
                          %{performance.overall_performance.last_7_days.accuracy_percentage}
                        </p>
                        <p className="text-blue-300 text-sm">
                          {performance.overall_performance.last_7_days.correct_predictions} / {performance.overall_performance.last_7_days.total_predictions} doğru
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Bet Type Performance */}
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h3 className="text-lg font-semibold text-white mb-4">📊 Bahis Türü Performansı</h3>
                    <div className="space-y-4">
                      {Object.entries(performance.bet_type_performance).map(([betType, stats]) => (
                        <div key={betType} className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <span className="text-2xl">{getBetTypeIcon(betType)}</span>
                            <div>
                              <p className="text-white font-medium">{betType}</p>
                              <p className="text-gray-400 text-sm">{stats.correct} / {stats.total} doğru</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-lg font-bold ${getConfidenceColor(stats.accuracy)}`}>
                              %{stats.accuracy}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* System Statistics */}
                  <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h3 className="text-lg font-semibold text-white mb-4">🖥️ Sistem İstatistikleri</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      <div>
                        <p className="text-gray-400 text-sm">Toplam Lig</p>
                        <p className="text-white text-xl font-bold">{systemStatus?.collections?.leagues?.total || 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-sm">Toplam Takım</p>
                        <p className="text-white text-xl font-bold">{systemStatus?.collections?.teams || 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-sm">Toplam Maç</p>
                        <p className="text-white text-xl font-bold">{systemStatus?.collections?.matches?.total || 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-sm">Toplam Tahmin</p>
                        <p className="text-white text-xl font-bold">{systemStatus?.collections?.predictions || 0}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-blue-300">Analitik verileri yükleniyor...</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;