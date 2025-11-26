-- INSERT statements for NFC/RFID cards
-- Vložení NFC/RFID kariet do databázy
-- Database: Traceability_TEST (TEST ENVIRONMENT)
-- Poznámka: Pre produkciu zmeňte na USE [Traceability]
-- 
-- POZNÁMKA: Karty sú už nastavené s reálnymi ID
-- NOTE: Cards are already set up with real IDs

USE [Traceability_TEST]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Insert first card - Maroš Machaj
-- Vložení první karty - Maroš Machaj
INSERT INTO [dbo].[nfc_rfid_cards] 
    ([card_id], [employee_name], [employee_id], [is_active], [created_by], [notes])
VALUES
    ('04:96:73:8A:9C:1B:90', N'Maroš Machaj', NULL, 1, N'System', N'Test card for Maroš Machaj');

-- Insert second card - Honza Supka
-- Vložení druhé karty - Honza Supka
INSERT INTO [dbo].[nfc_rfid_cards] 
    ([card_id], [employee_name], [employee_id], [is_active], [created_by], [notes])
VALUES
    ('04:B9:57:8A:9C:1B:90', N'Honza Supka', NULL, 1, N'System', N'Test card for Honza Supka');

GO

-- Verify inserted data / Ověření vložených dat
SELECT 
    [card_id],
    [employee_name],
    [employee_id],
    [is_active],
    [created_at],
    [last_used],
    [created_by],
    [notes]
FROM [dbo].[nfc_rfid_cards]
ORDER BY [created_at] DESC;

GO

PRINT 'NFC/RFID cards inserted successfully into TEST database.'
PRINT 'Cards:'
PRINT '  - 04:96:73:8A:9C:1B:90 -> Maroš Machaj'
PRINT '  - 04:B9:57:8A:9C:1B:90 -> Honza Supka'
GO

