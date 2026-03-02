/**
 * Authentic Leaders - Civ-Specific Icon Override UIScript
 *
 * Intercepts fxs-icon elements that display leader icons and swaps them
 * with civilization-specific variants for ALL players based on each
 * player's own civilization.
 *
 * Runs in game scope only — civ isn't known during leader select (shell scope).
 */
(function authenticLeadersIcons() {
    // Cache: playerId → { leaderType, civIconId } or null
    var playerIconCache = {};
    var localLeaderType = null;
    var localCivIconId = null;
    var initialized = false;

    /**
     * Initialize local player from Configuration (reliable).
     */
    function initLocalPlayer() {
        try {
            var playerConfig = Configuration.getPlayer(GameContext.localPlayerID);
            if (!playerConfig) return false;
            localLeaderType = playerConfig.leaderTypeName;
            var civType = playerConfig.civilizationTypeName;
            if (!localLeaderType || !civType) return false;
            var civSuffix = civType.replace("CIVILIZATION_", "");
            localCivIconId = localLeaderType + "_" + civSuffix;
            var testUrl = UI.getIconCSS(localCivIconId);
            if (!testUrl) {
                console.warn("[AuthenticLeaders] No civ-specific icon for " + localCivIconId);
                localCivIconId = null;
                return false;
            }
            console.log("[AuthenticLeaders] Local player " + GameContext.localPlayerID + ": " + localLeaderType + " -> " + localCivIconId);
            playerIconCache[GameContext.localPlayerID] = {
                leaderType: localLeaderType,
                civIconId: localCivIconId
            };
            return true;
        } catch (e) {
            console.warn("[AuthenticLeaders] Init failed: " + e);
            return false;
        }
    }

    /**
     * Build icon cache for all alive players using Players.getAlive(),
     * the same API the diplo-ribbon uses. This is more reliable than
     * individual Players.get() calls.
     */
    function buildPlayerMap() {
        try {
            var playerList = Players.getAlive();
            if (!playerList) {
                console.warn("[AuthenticLeaders] Players.getAlive() returned null");
                return;
            }
            for (var i = 0; i < playerList.length; i++) {
                var p = playerList[i];
                if (!p || !p.isMajor) continue;
                // Skip if already cached
                if (playerIconCache[p.id] !== undefined) continue;
                try {
                    // Both leaderType and civilizationType from Players API are
                    // internal values — need GameInfo lookups to get string IDs
                    var leaderInfo = GameInfo.Leaders.lookup(p.leaderType);
                    var leaderType = leaderInfo ? leaderInfo.LeaderType : null;
                    var civInfo = GameInfo.Civilizations.lookup(p.civilizationType);
                    var civType = civInfo ? civInfo.CivilizationType : null;
                    console.log("[AuthenticLeaders] Player " + p.id + ": leader=" + leaderType + " civ=" + civType);
                    if (!leaderType || !civType) {
                        playerIconCache[p.id] = null;
                        continue;
                    }
                    var civSuffix = civType.replace("CIVILIZATION_", "");
                    var civIconId = leaderType + "_" + civSuffix;
                    var testUrl = UI.getIconCSS(civIconId);
                    if (!testUrl) {
                        console.log("[AuthenticLeaders] Player " + p.id + ": no icon for " + civIconId + ", skipping");
                        playerIconCache[p.id] = null;
                        continue;
                    }
                    playerIconCache[p.id] = { leaderType: leaderType, civIconId: civIconId };
                    console.log("[AuthenticLeaders] Player " + p.id + ": " + leaderType + " -> " + civIconId);
                } catch (e) {
                    console.warn("[AuthenticLeaders] Error for player " + p.id + ": " + e);
                    playerIconCache[p.id] = null;
                }
            }
        } catch (e) {
            console.warn("[AuthenticLeaders] buildPlayerMap failed: " + e);
        }
    }

    function getPlayerIconInfo(playerId) {
        if (playerIconCache[playerId] !== undefined) {
            return playerIconCache[playerId];
        }
        // Not yet cached — rebuild the map (new players may have been met)
        buildPlayerMap();
        return playerIconCache[playerId] || null;
    }

    function processIconElement(el) {
        var id = el.getAttribute("data-icon-id");
        if (!id || !id.startsWith("LEADER_")) return;

        var info = null;
        var playerContainer = el.closest("[data-player-id]");
        if (playerContainer) {
            var playerId = parseInt(playerContainer.getAttribute("data-player-id"), 10);
            if (!isNaN(playerId)) {
                info = getPlayerIconInfo(playerId);
            }
        } else {
            // No player context — assume local player
            if (localLeaderType && localCivIconId) {
                info = { leaderType: localLeaderType, civIconId: localCivIconId };
            }
        }

        if (!info) return;
        if (id !== info.leaderType) return;

        var context = el.getAttribute("data-icon-context");
        var iconUrl = UI.getIconCSS(info.civIconId, context ? context : undefined);
        if (iconUrl) {
            el.style.backgroundImage = iconUrl;
        }
    }

    function processAllIcons() {
        document.querySelectorAll("fxs-icon").forEach(function(el) {
            processIconElement(el);
        });
    }

    var observer = new MutationObserver(function(mutations) {
        if (!initialized) return;
        for (var i = 0; i < mutations.length; i++) {
            var mutation = mutations[i];
            if (mutation.type === "attributes" && mutation.attributeName === "data-icon-id") {
                var target = mutation.target;
                if (target.tagName && target.tagName.toLowerCase() === "fxs-icon") {
                    setTimeout(processIconElement.bind(null, target), 0);
                }
            }
            if (mutation.type === "childList") {
                var added = mutation.addedNodes;
                for (var j = 0; j < added.length; j++) {
                    var node = added[j];
                    if (node.nodeType !== 1) continue;
                    if (node.tagName && node.tagName.toLowerCase() === "fxs-icon") {
                        setTimeout(processIconElement.bind(null, node), 0);
                    }
                    var children = node.querySelectorAll ? node.querySelectorAll("fxs-icon") : [];
                    for (var k = 0; k < children.length; k++) {
                        setTimeout(processIconElement.bind(null, children[k]), 0);
                    }
                }
            }
        }
    });

    function startObserving() {
        if (!initLocalPlayer()) {
            setTimeout(startObserving, 500);
            return;
        }
        // Build cache for all players
        buildPlayerMap();
        initialized = true;
        console.log("[AuthenticLeaders] Icon override system active, cached players: " + Object.keys(playerIconCache).length);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["data-icon-id"]
        });
        processAllIcons();
    }

    if (document.body) {
        startObserving();
    } else {
        document.addEventListener("DOMContentLoaded", startObserving);
    }
})();
