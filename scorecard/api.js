(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  var API = "https://statsapi.mlb.com/api/v1";
  var LIVE_API = "https://statsapi.mlb.com/api/v1.1";
  var cache = {};

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("API error: " + r.status);
      return r.json();
    });
  }

  SC.api = {
    fetchSchedule: function (dateStr) {
      var key = "sched:" + dateStr;
      if (cache[key]) return Promise.resolve(cache[key]);
      var url = API + "/schedule?sportId=1&date=" + dateStr +
        "&hydrate=team,linescore,decisions";
      return fetchJSON(url).then(function (data) {
        var games = (data.dates && data.dates[0] && data.dates[0].games) || [];
        cache[key] = games;
        return games;
      });
    },

    fetchGameFeed: function (gamePk) {
      var key = "feed:" + gamePk;
      if (cache[key]) return Promise.resolve(cache[key]);
      var url = LIVE_API + "/game/" + gamePk + "/feed/live";
      return fetchJSON(url).then(function (feed) {
        cache[key] = feed;
        return feed;
      });
    }
  };

  // Hardcoded 30 MLB teams
  SC.teams = [
    { id: 109, abbr: "ARI", name: "Arizona Diamondbacks" },
    { id: 144, abbr: "ATL", name: "Atlanta Braves" },
    { id: 110, abbr: "BAL", name: "Baltimore Orioles" },
    { id: 111, abbr: "BOS", name: "Boston Red Sox" },
    { id: 112, abbr: "CHC", name: "Chicago Cubs" },
    { id: 145, abbr: "CWS", name: "Chicago White Sox" },
    { id: 113, abbr: "CIN", name: "Cincinnati Reds" },
    { id: 114, abbr: "CLE", name: "Cleveland Guardians" },
    { id: 115, abbr: "COL", name: "Colorado Rockies" },
    { id: 116, abbr: "DET", name: "Detroit Tigers" },
    { id: 117, abbr: "HOU", name: "Houston Astros" },
    { id: 118, abbr: "KC", name: "Kansas City Royals" },
    { id: 108, abbr: "LAA", name: "Los Angeles Angels" },
    { id: 119, abbr: "LAD", name: "Los Angeles Dodgers" },
    { id: 146, abbr: "MIA", name: "Miami Marlins" },
    { id: 158, abbr: "MIL", name: "Milwaukee Brewers" },
    { id: 142, abbr: "MIN", name: "Minnesota Twins" },
    { id: 121, abbr: "NYM", name: "New York Mets" },
    { id: 147, abbr: "NYY", name: "New York Yankees" },
    { id: 133, abbr: "OAK", name: "Oakland Athletics" },
    { id: 143, abbr: "PHI", name: "Philadelphia Phillies" },
    { id: 134, abbr: "PIT", name: "Pittsburgh Pirates" },
    { id: 135, abbr: "SD", name: "San Diego Padres" },
    { id: 137, abbr: "SF", name: "San Francisco Giants" },
    { id: 136, abbr: "SEA", name: "Seattle Mariners" },
    { id: 138, abbr: "STL", name: "St. Louis Cardinals" },
    { id: 139, abbr: "TB", name: "Tampa Bay Rays" },
    { id: 140, abbr: "TEX", name: "Texas Rangers" },
    { id: 141, abbr: "TOR", name: "Toronto Blue Jays" },
    { id: 120, abbr: "WSH", name: "Washington Nationals" }
  ];
})();
