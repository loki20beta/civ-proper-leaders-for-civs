-- Restructure LoadingInfo_Leaders to support civilization-specific overrides.
-- The original table has LeaderType as sole PK, preventing multiple rows per leader.
-- We need composite PK (LeaderType, CivilizationTypeOverride) for civ-specific images.

-- Step 1: Backup existing data
CREATE TEMP TABLE _LIL_Backup AS SELECT * FROM LoadingInfo_Leaders;

-- Step 2: Drop the original table (single-column PK)
DROP TABLE IF EXISTS LoadingInfo_Leaders;

-- Step 3: Recreate with composite primary key (matches original column order)
CREATE TABLE 'LoadingInfo_Leaders' (
	'LeaderType' TEXT NOT NULL,
	'AgeTypeOverride' TEXT,
	'Audio' TEXT,
	'CivilizationTypeOverride' TEXT,
	'LeaderImage' TEXT,
	'LeaderNameTextOverride' LOC_TEXT,
	'LeaderText' LOC_TEXT,
	PRIMARY KEY("LeaderType", "CivilizationTypeOverride"),
	FOREIGN KEY ("LeaderType") REFERENCES "Leaders"("LeaderType") ON DELETE CASCADE ON UPDATE CASCADE
);

-- Step 4: Restore all existing data
INSERT INTO LoadingInfo_Leaders SELECT * FROM _LIL_Backup;

-- Step 5: Clean up backup
DROP TABLE _LIL_Backup;

-- Step 6: Update default Augustus image to our custom portrait
UPDATE LoadingInfo_Leaders
SET LeaderImage = 'fs://game/authentic-leaders/images/loading/lsl_augustus.png'
WHERE LeaderType = 'LEADER_AUGUSTUS' AND CivilizationTypeOverride IS NULL;

-- Step 7: Insert civ-specific Augustus loading screens for all antiquity civilizations
-- Base game civs
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_AKSUM', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_aksum.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_EGYPT', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_egypt.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_GREECE', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_greece.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_HAN', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_han.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_KHMER', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_khmer.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_MAURYA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_maurya.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_MAYA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_maya.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_MISSISSIPPIAN', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_mississippian.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_PERSIA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_persia.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_ROME', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_rome.png', 'VO_Loading2_AUGUSTUS');

-- DLC civs
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_ASSYRIA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_assyria.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_CARTHAGE', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_carthage.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_SILLA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_silla.png', 'VO_Loading2_AUGUSTUS');
INSERT INTO LoadingInfo_Leaders (LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES
('LEADER_AUGUSTUS', 'CIVILIZATION_TONGA', 'LOC_LOADING_LEADER_INTRO_TEXT_AUGUSTUS', 'fs://game/authentic-leaders/images/loading/lsl_augustus_tonga.png', 'VO_Loading2_AUGUSTUS');
