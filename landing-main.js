var teams = window.__TEAMS || [];
var LOGO = "https://www.mlbstatic.com/team-logos/team-cap-on-dark/";
var API = "https://statsapi.mlb.com/api/v1";

var divOrder = [
  {key:"AL",league:"American League",divs:["AL East","AL Central","AL West"]},
  {key:"NL",league:"National League",divs:["NL East","NL Central","NL West"]}
];

var teamById = {};
var teamBySlug = {};
for (var i = 0; i < teams.length; i++) {
  teamById[teams[i].id] = teams[i];
  teamBySlug[teams[i].slug] = teams[i];
}

var byDiv = {};
for (var i2 = 0; i2 < teams.length; i2++) {
  var d = teams[i2].division_name;
  if (!byDiv[d]) byDiv[d] = [];
  byDiv[d].push(teams[i2]);
}

(function(){
  var now = new Date();
  var opts = { weekday:"short", month:"short", day:"2-digit", year:"numeric" };
  var s = now.toLocaleDateString("en-US", opts).toUpperCase().replace(/,/g,"").replace(/\s+/g," ");
  var parts = s.split(" ");
  if (parts.length === 4) s = parts[0] + " · " + parts[1] + " " + parts[2] + " · " + parts[3];
  document.getElementById("ticker-date").textContent = s;
})();

var container = document.getElementById("leagues");

for (var li = 0; li < divOrder.length; li++) {
  var lg = divOrder[li];
  var teamCount = 0;
  for (var dc = 0; dc < lg.divs.length; dc++) teamCount += (byDiv[lg.divs[dc]] || []).length;

  var section = document.createElement("section");
  section.className = "league";
  section.innerHTML =
    '<div class="league-head">' +
      '<span class="num">' + lg.key + '</span>' +
      '<h2 class="h">' + lg.league + '</h2>' +
      '<span class="tag">' + teamCount + ' Teams</span>' +
    '</div>';

  for (var di = 0; di < lg.divs.length; di++) {
    var divName = lg.divs[di];
    var group = document.createElement("div");
    group.className = "div-group";
    group.innerHTML = '<div class="div-label">' + divName + '</div>';

    var list = document.createElement("div");
    list.className = "div-teams";
    list.id = "div-" + divName.replace(/\s/g, "-");

    var dt = (byDiv[divName] || []).slice();
    dt.sort(function(a,b){ return a.full_name.localeCompare(b.full_name); });

    for (var ti = 0; ti < dt.length; ti++) {
      var t = dt[ti];
      var a = document.createElement("a");
      a.className = "team-card";
      a.id = "card-" + t.id;
      a.href = t.slug + "/";
      a.style.borderLeftColor = t.colors.primary;
      a.innerHTML =
        '<img class="team-logo" src="' + LOGO + t.id + '.svg" alt="" loading="lazy">' +
        '<div class="team-info">' +
          '<div class="team-name">' + t.full_name + '</div>' +
          '<div class="team-meta">' +
            '<span class="team-rec" id="rec-' + t.id + '"></span>' +
            '<span class="team-streak" id="streak-' + t.id + '"></span>' +
          '</div>' +
        '</div>' +
        '<span class="team-gb" id="gb-' + t.id + '"></span>' +
        '<span class="team-live empty" id="live-' + t.id + '"></span>';
      list.appendChild(a);
    }
    group.appendChild(list);
    section.appendChild(group);
  }
  container.appendChild(section);
}

fetch(API + "/standings?leagueId=103,104&season=" + new Date().getFullYear() + "&standingsTypes=regularSeason")
  .then(function(r){ return r.json(); })
  .then(function(data) {
    var divMap = {201:"AL-East",202:"AL-Central",200:"AL-West",204:"NL-East",205:"NL-Central",203:"NL-West"};
    for (var ri = 0; ri < data.records.length; ri++) {
      var rec = data.records[ri];
      var listEl = document.getElementById("div-" + divMap[rec.division.id]);
      if (!listEl) continue;

      var sorted = rec.teamRecords.slice().sort(function(a,b){
        return parseInt(a.divisionRank) - parseInt(b.divisionRank);
      });

      for (var si = 0; si < sorted.length; si++) {
        var tr = sorted[si];
        var tid = tr.team.id;
        var recEl = document.getElementById("rec-" + tid);
        var streakEl = document.getElementById("streak-" + tid);
        var gbEl = document.getElementById("gb-" + tid);

        if (recEl) recEl.textContent = tr.wins + "-" + tr.losses;
        if (streakEl) {
          var sc = tr.streak ? tr.streak.streakCode : "";
          streakEl.textContent = sc;
          streakEl.classList.remove("hot","cold");
          if (sc) {
            var n = parseInt(sc.slice(1),10) || 0;
            if (sc[0] === "W" && n >= 3) streakEl.classList.add("hot");
            else if (sc[0] === "L" && n >= 3) streakEl.classList.add("cold");
          }
        }
        if (gbEl) {
          var gb = tr.gamesBack;
          gbEl.textContent = (gb === "-" || gb === "0.0") ? "—" : gb;
        }

        var card = document.getElementById("card-" + tid);
        if (card) listEl.appendChild(card);
      }
    }
  })
  .catch(function(){});

var latestGamesByTeam = {};

function fmtTime(iso){
  try {
    var d = new Date(iso);
    return d.toLocaleTimeString("en-US", {hour:"numeric",minute:"2-digit",timeZone:"America/Chicago"});
  } catch(e){ return ""; }
}

fetch(API + "/schedule?sportId=1&date=" + new Date().toISOString().slice(0,10) + "&hydrate=team,linescore")
  .then(function(r){ return r.json(); })
  .then(function(data) {
    var dates = data.dates || [];
    var games = dates.length ? (dates[0].games || []) : [];

    var nLive = 0, nFinal = 0, nPreview = 0;

    for (var gi = 0; gi < games.length; gi++) {
      var g = games[gi];
      var state = g.status.abstractGameState;
      if (state === "Live") nLive++;
      else if (state === "Final") nFinal++;
      else nPreview++;

      var away = g.teams.away, home = g.teams.home;
      var pair = [[away.team.id, true, home.team], [home.team.id, false, away.team]];

      for (var pi = 0; pi < pair.length; pi++) {
        var tid = pair[pi][0];
        var isAway = pair[pi][1];
        var opp = pair[pi][2];
        var isHome = !isAway;
        var oppAbbr = opp.abbreviation;
        var prefix = isHome ? "vs" : "@";
        var el = document.getElementById("live-" + tid);
        var card = document.getElementById("card-" + tid);
        if (!el) continue;
        el.classList.remove("empty");

        if (state === "Live") {
          var ls = g.linescore || {};
          var as = away.score || 0, hs = home.score || 0;
          var inn = ls.currentInningOrdinal || "";
          var half = ls.isTopInning ? "T" : "B";
          el.className = "team-live";
          el.innerHTML = '<span class="dot"></span>' + as + "-" + hs + " " + half + inn;
          if (card) card.classList.add("has-live");
          latestGamesByTeam[tid] = { state:"Live", away:away, home:home, linescore:ls, isHome:isHome, opp:oppAbbr };
        } else if (state === "Final") {
          var as2 = away.score || 0, hs2 = home.score || 0;
          var myScore = isHome ? hs2 : as2;
          var oppScore = isHome ? as2 : hs2;
          var won = myScore > oppScore;
          el.className = "team-final " + (won ? "w" : "l");
          el.textContent = (won ? "W " : "L ") + myScore + "-" + oppScore + " " + prefix + " " + oppAbbr;
          latestGamesByTeam[tid] = { state:"Final", won:won, myScore:myScore, oppScore:oppScore, prefix:prefix, opp:oppAbbr };
        } else {
          var time = fmtTime(g.gameDate);
          el.className = "team-preview";
          el.textContent = prefix + " " + oppAbbr + " " + time;
          latestGamesByTeam[tid] = { state:"Preview", prefix:prefix, opp:oppAbbr, time:time };
        }
      }
    }

    document.getElementById("ticker-live").textContent = nLive + " Live";
    document.getElementById("ticker-final").textContent = nFinal + " Final";
    document.getElementById("ticker-preview").textContent = nPreview + " Upcoming";
    document.getElementById("ticker-dot").style.display = nLive > 0 ? "inline-block" : "none";
    document.getElementById("stat-games").textContent = games.length;
    document.getElementById("stat-live").textContent = nLive;
    document.getElementById("stat-final").textContent = nFinal;
    document.getElementById("kick-games").textContent = games.length + " Games";

    var sub = document.getElementById("greet-sub");
    if (nLive > 0) sub.innerHTML = 'Your briefings are ready <span class="g">·</span> <span class="paper">' + nLive + ' live game' + (nLive===1?"":"s") + ' right now</span>';
    else if (games.length) sub.innerHTML = 'Your briefings are ready <span class="g">·</span> <span class="paper">' + games.length + ' games on today\'s slate</span>';
    else sub.textContent = 'Your briefings are ready — no MLB action today';

    if (window.__heroTeamSlug && window.fillHero) window.fillHero(window.__heroTeamSlug);
  })
  .catch(function(){});

window.fillHero = function(slug){
  var t = teamBySlug[slug];
  if (!t) return;
  var yt = document.getElementById("your-team");
  var card = document.getElementById("yt-card");
  var logo = document.getElementById("yt-logo");
  var name = document.getElementById("yt-name");
  var line = document.getElementById("yt-line");
  var kicker = document.getElementById("yt-kicker");

  card.href = t.slug + "/";
  logo.src = LOGO + t.id + ".svg";
  var shortName = t.name || t.full_name.split(" ").pop();
  name.textContent = "The " + shortName;
  card.style.background = "linear-gradient(90deg," + hexA(t.colors.primary, .38) + " 0%, var(--ink-2) 60%, var(--ink-2) 100%)";
  card.style.borderLeftColor = t.colors.accent || t.colors.primary;

  var gridCard = document.getElementById("card-" + t.id);
  if (gridCard) {
    gridCard.classList.add("is-user");
    gridCard.style.borderLeftColor = "var(--gold)";
  }
  document.getElementById("kick-team").textContent = shortName;

  var g = latestGamesByTeam[t.id];
  var parts = [];
  if (g) {
    if (g.state === "Live") {
      var ls = g.linescore || {};
      var as = g.away.score || 0, hs = g.home.score || 0;
      var inn = ls.currentInningOrdinal || "";
      var half = ls.isTopInning ? "Top" : "Bot";
      var myScore = g.isHome ? hs : as;
      var oppScore = g.isHome ? as : hs;
      var lead = myScore > oppScore ? "win" : (myScore < oppScore ? "loss" : "g");
      parts.push('<span class="' + lead + '">LIVE ' + myScore + '–' + oppScore + '</span>');
      parts.push((g.isHome ? "vs " : "@ ") + g.opp);
      parts.push(half + " " + inn);
      kicker.textContent = "◆ Your Team · Live Now";
    } else if (g.state === "Final") {
      parts.push('<span class="' + (g.won ? "win" : "loss") + '">' + (g.won ? "W " : "L ") + g.myScore + "–" + g.oppScore + '</span>');
      parts.push(g.prefix + " " + g.opp);
      kicker.textContent = "◆ Your Team · Last Game";
    } else {
      parts.push("Today " + g.prefix + " " + g.opp);
      if (g.time) parts.push(g.time);
      kicker.textContent = "◆ Your Team · Today's Slate";
    }
  } else {
    parts.push("Off day");
    kicker.textContent = "◆ Your Team · Fresh Briefing";
  }
  parts.push('<span class="g">' + (t.division_name || "") + '</span>');
  line.innerHTML = parts.join(' <span class="g">·</span> ');
  yt.hidden = false;
};

function hexA(hex, a){
  var h = (hex || "#0e3386").replace("#","");
  if (h.length === 3) h = h.split("").map(function(c){return c+c;}).join("");
  var r = parseInt(h.slice(0,2),16), gg = parseInt(h.slice(2,4),16), bb = parseInt(h.slice(4,6),16);
  return "rgba(" + r + "," + gg + "," + bb + "," + a + ")";
}
