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
    // Persona types → base leader type (for civ-specific icon ID construction)
    // Civ icons are registered under base types (e.g., LEADER_ASHOKA_ROME),
    // so persona types must map back to base before appending civ suffix.
    var PERSONA_TO_BASE = {
        "LEADER_ASHOKA_ALT": "LEADER_ASHOKA",
        "LEADER_FRIEDRICH_ALT": "LEADER_FRIEDRICH",
        "LEADER_HIMIKO_ALT": "LEADER_HIMIKO",
        "LEADER_NAPOLEON_ALT": "LEADER_NAPOLEON",
        "LEADER_XERXES_ALT": "LEADER_XERXES"
    };

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
            var baseType = PERSONA_TO_BASE[localLeaderType] || localLeaderType;
            localCivIconId = baseType + "_" + civSuffix;
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
                    var baseType = PERSONA_TO_BASE[leaderType] || leaderType;
                    var civIconId = baseType + "_" + civSuffix;
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
        // Match icon if it uses the player's leader type OR the base type
        // (persona icons may use either the persona type or the base type)
        var baseForPlayer = PERSONA_TO_BASE[info.leaderType] || info.leaderType;
        if (id !== info.leaderType && id !== baseForPlayer) return;

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

    // --- Path B: getLeaderPortraitIcon() background-image swapping ---
    // Many UI contexts (relationship panel, city banners, combat preview, etc.)
    // use getLeaderPortraitIcon() which renders into plain <div> elements.
    // We intercept by matching backgroundImage URLs and swapping to civ-specific paths.

    // Map: lowercased base URL prefix → lowercased civ URL prefix
    // e.g. "fs://game/.../lp_hex_amina" → "fs://game/.../rome/lp_hex_amina_rome"
    var portraitUrlSwapMap = {};

    function buildPortraitSwapMap() {
        portraitUrlSwapMap = {};
        for (var pid in playerIconCache) {
            var info = playerIconCache[pid];
            if (!info) continue;
            try {
                var baseUrl = UI.getIconURL(info.leaderType, "LEADER");
                var civUrl = UI.getIconURL(info.civIconId, "LEADER");
                if (baseUrl && civUrl && baseUrl !== civUrl) {
                    portraitUrlSwapMap[baseUrl.toLowerCase()] = civUrl.toLowerCase();
                }
            } catch (e) {
                // Skip players where URL lookup fails
            }
        }
        console.log("[AuthenticLeaders] Portrait swap map: " + Object.keys(portraitUrlSwapMap).length + " entries");
    }

    function swapPortraitBackground(el) {
        var bg = el.style.backgroundImage;
        if (!bg || bg.indexOf("lp_") === -1) return;
        var bgLower = bg.toLowerCase();
        for (var baseUrl in portraitUrlSwapMap) {
            if (bgLower.indexOf(baseUrl) !== -1) {
                el.style.backgroundImage = bgLower.replace(baseUrl, portraitUrlSwapMap[baseUrl]);
                return;
            }
        }
    }

    function processPortraitNodes(rootNode) {
        if (rootNode.nodeType !== 1) return;
        swapPortraitBackground(rootNode);
        var all = rootNode.getElementsByTagName("*");
        for (var i = 0; i < all.length; i++) {
            swapPortraitBackground(all[i]);
        }
    }

    function processAllPortraits() {
        processPortraitNodes(document.body);
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
                    // Path B: swap portrait backgrounds on newly added nodes
                    setTimeout(processPortraitNodes.bind(null, node), 0);
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
        // Build URL swap map for Path B portrait interception
        buildPortraitSwapMap();
        initialized = true;
        console.log("[AuthenticLeaders] Icon override system active, cached players: " + Object.keys(playerIconCache).length);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["data-icon-id"]
        });
        processAllIcons();
        processAllPortraits();
    }

    if (document.body) {
        startObserving();
    } else {
        document.addEventListener("DOMContentLoaded", startObserving);
    }
})();
