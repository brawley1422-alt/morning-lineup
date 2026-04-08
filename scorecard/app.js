(function () {
  "use strict";
  var SC = window.Scorecard = window.Scorecard || {};

  var mainEl = null;

  function getParams() {
    var params = {};
    var search = window.location.search.slice(1);
    if (!search) return params;
    var parts = search.split("&");
    for (var i = 0; i < parts.length; i++) {
      var kv = parts[i].split("=");
      params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    }
    return params;
  }

  SC.app = {
    view: "finder",
    embed: false,

    init: function () {
      mainEl = document.getElementById("main");
      SC.tooltip.init();

      var params = getParams();
      this.embed = params.embed === "1";

      if (this.embed) {
        document.body.classList.add("embed-mode");
      }

      if (params.game) {
        this.loadGame(parseInt(params.game, 10));
      } else {
        if (params.date) {
          SC.finder.currentDate = params.date;
        }
        this.showFinder();
      }

      // Handle browser back/forward
      window.addEventListener("popstate", function () {
        var p = getParams();
        if (p.game) {
          SC.app.loadGame(parseInt(p.game, 10), true);
        } else {
          if (p.date) SC.finder.currentDate = p.date;
          SC.app.showFinder(true);
        }
      });
    },

    showFinder: function (skipPush) {
      this.view = "finder";
      if (!skipPush) this.updateURL();
      SC.finder.render(mainEl);
    },

    loadGame: function (gamePk, skipPush) {
      var self = this;
      this.view = "scorecard";
      if (!skipPush) {
        var url = "?game=" + gamePk;
        history.pushState({ game: gamePk }, "", url);
      }

      mainEl.innerHTML = '<div class="loading">Loading scorecard...</div>';

      SC.api.fetchGameFeed(gamePk).then(function (feed) {
        var model = SC.parser.parse(feed);
        self.renderScorecard(model);
      }).catch(function (err) {
        var msg = String(err.message || "Unknown error").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
        mainEl.innerHTML = '<div class="error-state">Failed to load game: ' +
          msg + '</div>' +
          '<button class="back-btn" onclick="Scorecard.app.showFinder()">&larr; Back to games</button>';
      });
    },

    renderScorecard: function (model) {
      var html = '';
      if (!this.embed) {
        html += '<button class="back-btn" onclick="Scorecard.app.showFinder()">&larr; Back to games</button>';
      }
      html += SC.header.render(model);
      html += SC.scorebook.render(model);
      mainEl.innerHTML = html;

      // In embed mode, tell parent frame our height
      if (this.embed && window.parent !== window) {
        try {
          var h = document.documentElement.scrollHeight;
          window.parent.postMessage({ type: "scorecard-height", height: h }, "*");
        } catch (e) {}
      }
    },

    updateURL: function () {
      var params = [];
      if (SC.finder.currentDate) params.push("date=" + SC.finder.currentDate);
      var url = params.length ? "?" + params.join("&") : window.location.pathname;
      history.replaceState({}, "", url);
    }
  };

  // Boot
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { SC.app.init(); });
  } else {
    SC.app.init();
  }
})();
