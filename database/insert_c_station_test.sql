-- INSERT statements for c_station table in TEST database
-- Vložení hodnot do tabulky c_station v TEST databázi
-- Database: Traceability_TEST

USE [Traceability_TEST]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Clear existing data if needed (optional - uncomment if you want to delete existing records)
-- Vymazání existujících dat (volitelné - odkomentuj, pokud chceš smazat existující záznamy)
-- DELETE FROM [dbo].[c_station];
-- GO

-- Insert station data / Vložení dat stanic
INSERT INTO [dbo].[c_station] ([station_id], [station_name], [station_description])
VALUES
    (1, N'Kovací linka', N'Pracoviště pro kování dílů'),
    (2, N'Test tvrdosti', N'Pracoviště pro testování tvrdosti materiálu'),
    (3, N'Penetrace', N'Pracoviště pro penetrační testy'),
    (4, N'Tryskání', N'Pracoviště pro tryskání povrchu'),
    (5, N'Kontrola kvality', N'Pracoviště pro kontrolu kvality'),
    (6, N'Přeskladnění', N'Pracoviště pro expedici'),
    (7, N'Laboratoř', N'Laboratoř pro speciální testy'),
    (8, N'Penetrace rework', N'Pracoviště pro opakovanou penetraci'),
    (9, N'Tryskání rework', N'Pracoviště pro opakované tryskání'),
    (10, N'Kontrola kvality rework', N'Pracoviště pro opakovanou kontrolu kvality'),
    (11, N'Destruktivní kontrola', N'Pracoviště pro destruktivní testy'),
    (12, N'Kontrola kvality kování', N'Kontrola kvality po kování s protokolem'),
    (13, N'LAB_Rework', N'Laboratoř rework - oprava dílů z KKK nebo Laboratoře'),
    (999, N'Virtual', N'Virtuální stanice - automatické OK po obou kontrolách');

GO

-- Verify inserted data / Ověření vložených dat
SELECT 
    [station_id],
    [station_name],
    [station_description]
FROM [dbo].[c_station]
ORDER BY [station_id];

GO

