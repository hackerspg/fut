import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [systemStatus, setSystemStatus] = useState(null);
  const [leagues, setLeagues] = useState([]);
  const [todayPredictions, setTodayPredictions] = useState([]);
  const [upcomingMatches, setUpcomingMatches] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('predictions');

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
      
      // Yaklaşan maçları getir
      const matchesResponse = await axios.get(`${API}/matches/upcoming`);
      setUpcomingMatches(matchesResponse.data.matches);
      
      // Performans istatistiklerini getir
      const performanceResponse = await axios.get(`${API}/stats/performance`);
      setPerformance(performanceResponse.data);
      
    } catch (error) {
      console.error('Veri yükleme hatası:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerScraper = async () => {
    try {
      await axios.post(`${API}/scraper/run`);
      alert('Veri toplama işlemi başlatıldı!');
    } catch (error) {
      console.error('Scraper başlatılamadı:', error);
      alert('Veri toplama işlemi başlatılamadı!');
    }
  };

  const generatePredictions = async () => {
    try {
      await axios.post(`${API}/prediction/generate`);
      alert('Tahmin üretme işlemi başlatıldı!');
    } catch (error) {
      console.error('Tahmin üretme başlatılamadı:', error);
      alert('Tahmin üretme işlemi başlatılamadı!');
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getBetTypeIcon = (betType) => {
    switch (betType) {
      case '1X2': return '🎯';
      case 'O/U2.5': return '⚽';
      case 'BTTS': return '🔄';
      default: return '📊';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-yellow-400 mx-auto"></div>
          <p className="text-white mt-4 text-xl">Sistem yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-3xl">🎯</div>
              <div>
                <h1 className="text-2xl font-bold text-white">Bahis Tahmin Sistemi</h1>
                <p className="text-blue-300 text-sm">50+ Ligden AI Destekli Tahminler</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={triggerScraper}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                🔄 Veri Topla
              </button>
              <button
                onClick={generatePredictions}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                🧠 Tahmin Üret
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Status Cards */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Sistem Durumu</p>
                <p className="text-white text-xl font-bold">
                  {systemStatus?.status === 'healthy' ? '✅ Çalışıyor' : '❌ Hata'}
                </p>
              </div>
              <div className="text-3xl">🖥️</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Aktif Ligler</p>
                <p className="text-white text-xl font-bold">{leagues.length}</p>
              </div>
              <div className="text-3xl">🏆</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Bugünkü Tahminler</p>
                <p className="text-white text-xl font-bold">{todayPredictions.length}</p>
              </div>
              <div className="text-3xl">📈</div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm">Başarı Oranı</p>
                <p className="text-white text-xl font-bold">
                  {performance?.accuracy_percentage || 0}%
                </p>
              </div>
              <div className="text-3xl">🎯</div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('predictions')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'predictions'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            📊 Bugünkü Tahminler
          </button>
          <button
            onClick={() => setActiveTab('matches')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'matches'
                ? 'bg-blue-600 text-white'
                : 'bg-white/10 text-blue-300 hover:bg-white/20'
            }`}
          >
            ⚽ Yaklaşan Maçlar
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
        </div>

        {/* Content */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
          {activeTab === 'predictions' && (
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">📊 Bugünkü Tahminler</h2>
              
              {todayPredictions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-blue-300 text-lg">Bugün için tahmin bulunmuyor.</p>
                  <p className="text-gray-400 mt-2">Veri toplama işlemini başlatarak tahminler üretebilirsiniz.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {todayPredictions.map((prediction, index) => (
                    <div key={index} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="flex items-center justify-between mb-2">
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
                          <p className={`font-bold ${getConfidenceColor(prediction.confidence)}`}>
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
                        </div>
                        <div className="text-right">
                          <p className="text-green-400 font-bold">
                            {prediction.suggested_odds && `Oran: ${prediction.suggested_odds}`}
                          </p>
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
              <h2 className="text-xl font-bold text-white mb-4">⚽ Yaklaşan Maçlar</h2>
              
              {upcomingMatches.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-blue-300 text-lg">Yaklaşan maç bulunmuyor.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {upcomingMatches.map((match, index) => (
                    <div key={index} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="text-center">
                            <p className="text-white font-bold">{match.home_team_name}</p>
                            <p className="text-blue-300 text-sm">vs</p>
                            <p className="text-white font-bold">{match.away_team_name}</p>
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <p className="text-blue-300 text-sm">{match.league_name}</p>
                          <p className="text-white">
                            {new Date(match.match_date).toLocaleDateString('tr-TR')}
                          </p>
                          <p className="text-gray-400 text-sm">
                            {new Date(match.match_date).toLocaleTimeString('tr-TR', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
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
                    <div key={index} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-white font-bold">{league.name}</h3>
                        <span className="text-blue-400 text-sm">{league.country}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-gray-400 text-sm">Sezon: {league.season}</p>
                        <span className="bg-green-600 text-white px-2 py-1 rounded text-xs">
                          {league.active ? 'Aktif' : 'Pasif'}
                        </span>
                      </div>
                    </div>
                  ))}
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