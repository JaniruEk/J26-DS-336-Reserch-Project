"""Build eval/hard_pairs.json: questions that need several table joins AND aggregation (the hardest SQL for small models).
- Spider dev: every question whose gold SQL has >= 2 JOINs and an aggregate (nested/compound skipped). Unseen: not in
  eval/spider_pairs.json, never used for tuning.
- Hand-written business questions on Chinook and Northwind, 2-5 joins, each naming its exact output columns (scoring
  compares result rows, column order included). Every gold query is run here and must return rows.
Usage: python -m scripts.make_hard_pairs   (needs data/spider.zip, data/chinook.db, data/northwind.db)"""
import json
import re
import sqlite3
import time
import zipfile

CH, NW = "data/chinook.db", "data/northwind.db"
OD = '"Order Details"'
HAND = [
    (CH, "For each genre, return the genre name and the total quantity of its tracks sold on invoice lines.",
     "SELECT g.Name, SUM(il.Quantity) FROM Genre g JOIN Track t ON t.GenreId = g.GenreId JOIN InvoiceLine il ON il.TrackId = t.TrackId GROUP BY g.Name"),
    (CH, "Return each artist's name and the number of tracks the artist has.",
     "SELECT ar.Name, COUNT(*) FROM Artist ar JOIN Album al ON al.ArtistId = ar.ArtistId JOIN Track t ON t.AlbumId = al.AlbumId GROUP BY ar.Name"),
    (CH, "For each support employee, return the employee's first name, last name and the total invoice amount of the customers they support.",
     "SELECT e.FirstName, e.LastName, SUM(i.Total) FROM Employee e JOIN Customer c ON c.SupportRepId = e.EmployeeId JOIN Invoice i ON i.CustomerId = c.CustomerId GROUP BY e.EmployeeId"),
    (CH, "For each customer country, return the country and the number of distinct genres its customers bought.",
     "SELECT c.Country, COUNT(DISTINCT t.GenreId) FROM Customer c JOIN Invoice i ON i.CustomerId = c.CustomerId JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId GROUP BY c.Country"),
    (CH, "Return the 5 artists with the highest sales revenue: the artist name and the revenue, computed as the sum of invoice line unit price times quantity.",
     "SELECT ar.Name, SUM(il.UnitPrice * il.Quantity) AS revenue FROM Artist ar JOIN Album al ON al.ArtistId = ar.ArtistId JOIN Track t ON t.AlbumId = al.AlbumId JOIN InvoiceLine il ON il.TrackId = t.TrackId GROUP BY ar.Name ORDER BY revenue DESC LIMIT 5"),
    (CH, "Which customers bought Rock tracks? Return each customer's first name, last name and the total quantity of Rock tracks they bought.",
     "SELECT c.FirstName, c.LastName, SUM(il.Quantity) FROM Customer c JOIN Invoice i ON i.CustomerId = c.CustomerId JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = 'Rock' GROUP BY c.CustomerId"),
    (CH, "Return the playlist id, playlist name and number of distinct artists for playlists containing tracks by more than 10 different artists.",
     "SELECT p.PlaylistId, p.Name, COUNT(DISTINCT al.ArtistId) FROM Playlist p JOIN PlaylistTrack pt ON pt.PlaylistId = p.PlaylistId JOIN Track t ON t.TrackId = pt.TrackId JOIN Album al ON al.AlbumId = t.AlbumId GROUP BY p.PlaylistId HAVING COUNT(DISTINCT al.ArtistId) > 10"),
    (CH, "For each media type, return the media type name and the total revenue from its invoice lines (unit price times quantity).",
     "SELECT m.Name, SUM(il.UnitPrice * il.Quantity) FROM MediaType m JOIN Track t ON t.MediaTypeId = m.MediaTypeId JOIN InvoiceLine il ON il.TrackId = t.TrackId GROUP BY m.Name"),
    (CH, "For albums by the artist AC/DC, return each album title and the album's total track length in milliseconds.",
     "SELECT al.Title, SUM(t.Milliseconds) FROM Album al JOIN Artist ar ON ar.ArtistId = al.ArtistId JOIN Track t ON t.AlbumId = al.AlbumId WHERE ar.Name = 'AC/DC' GROUP BY al.Title"),
    (CH, "For each support employee, return the employee's first name, last name and the number of distinct tracks sold to the customers they support.",
     "SELECT e.FirstName, e.LastName, COUNT(DISTINCT il.TrackId) FROM Employee e JOIN Customer c ON c.SupportRepId = e.EmployeeId JOIN Invoice i ON i.CustomerId = c.CustomerId JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId GROUP BY e.EmployeeId"),
    (CH, "Return the names of genres whose tracks appear on more than 100 invoice lines, with the number of those invoice lines.",
     "SELECT g.Name, COUNT(*) FROM Genre g JOIN Track t ON t.GenreId = g.GenreId JOIN InvoiceLine il ON il.TrackId = t.TrackId GROUP BY g.Name HAVING COUNT(*) > 100"),
    (CH, "Which customers bought tracks by Iron Maiden? Return each customer's first name, last name and the total quantity of Iron Maiden tracks they bought.",
     "SELECT c.FirstName, c.LastName, SUM(il.Quantity) FROM Customer c JOIN Invoice i ON i.CustomerId = c.CustomerId JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Album al ON al.AlbumId = t.AlbumId JOIN Artist ar ON ar.ArtistId = al.ArtistId WHERE ar.Name = 'Iron Maiden' GROUP BY c.CustomerId"),
    (NW, "For each product category, return the category name and the total quantity of its products ordered.",
     f"SELECT c.CategoryName, SUM(od.Quantity) FROM Categories c JOIN Products p ON p.CategoryID = c.CategoryID JOIN {OD} od ON od.ProductID = p.ProductID GROUP BY c.CategoryName"),
    (NW, "For each employee, return the first name, last name and the total sales value of their orders, computed as order line unit price times quantity (ignore discounts).",
     f"SELECT e.FirstName, e.LastName, SUM(od.UnitPrice * od.Quantity) FROM Employees e JOIN Orders o ON o.EmployeeID = e.EmployeeID JOIN {OD} od ON od.OrderID = o.OrderID GROUP BY e.EmployeeID"),
    (NW, "For each customer country, return the country and the number of distinct products ordered by customers in that country.",
     f"SELECT cu.Country, COUNT(DISTINCT od.ProductID) FROM Customers cu JOIN Orders o ON o.CustomerID = cu.CustomerID JOIN {OD} od ON od.OrderID = o.OrderID GROUP BY cu.Country"),
    (NW, "For each supplier country, return the country and the total quantity of that country's suppliers' products ordered.",
     f"SELECT s.Country, SUM(od.Quantity) FROM Suppliers s JOIN Products p ON p.SupplierID = s.SupplierID JOIN {OD} od ON od.ProductID = p.ProductID GROUP BY s.Country"),
    (NW, "For each product category, return the category name and the number of distinct customers who ordered products in that category.",
     f"SELECT c.CategoryName, COUNT(DISTINCT o.CustomerID) FROM Categories c JOIN Products p ON p.CategoryID = c.CategoryID JOIN {OD} od ON od.ProductID = p.ProductID JOIN Orders o ON o.OrderID = od.OrderID GROUP BY c.CategoryName"),
    (NW, "For each region, return the region description and the number of distinct employees assigned to territories in that region.",
     "SELECT r.RegionDescription, COUNT(DISTINCT et.EmployeeID) FROM Regions r JOIN Territories t ON t.RegionID = r.RegionID JOIN EmployeeTerritories et ON et.TerritoryID = t.TerritoryID GROUP BY r.RegionDescription"),
    (NW, "For each employee, return the first name, last name and the number of distinct product categories they have sold.",
     f"SELECT e.FirstName, e.LastName, COUNT(DISTINCT p.CategoryID) FROM Employees e JOIN Orders o ON o.EmployeeID = e.EmployeeID JOIN {OD} od ON od.OrderID = o.OrderID JOIN Products p ON p.ProductID = od.ProductID GROUP BY e.EmployeeID"),
    (NW, "Return the company names of customers who ordered products from all 8 categories, with the number of categories they ordered from.",
     f"SELECT cu.CompanyName, COUNT(DISTINCT p.CategoryID) FROM Customers cu JOIN Orders o ON o.CustomerID = cu.CustomerID JOIN {OD} od ON od.OrderID = o.OrderID JOIN Products p ON p.ProductID = od.ProductID GROUP BY cu.CustomerID HAVING COUNT(DISTINCT p.CategoryID) = 8"),
    (NW, "For each supplier, return the supplier's company name and the number of distinct customers who ordered that supplier's products.",
     f"SELECT s.CompanyName, COUNT(DISTINCT o.CustomerID) FROM Suppliers s JOIN Products p ON p.SupplierID = s.SupplierID JOIN {OD} od ON od.ProductID = p.ProductID JOIN Orders o ON o.OrderID = od.OrderID GROUP BY s.SupplierID"),
    (NW, "For each region, return the region description and the number of distinct orders taken by employees assigned to territories in that region.",
     "SELECT r.RegionDescription, COUNT(DISTINCT o.OrderID) FROM Regions r JOIN Territories t ON t.RegionID = r.RegionID JOIN EmployeeTerritories et ON et.TerritoryID = t.TerritoryID JOIN Orders o ON o.EmployeeID = et.EmployeeID GROUP BY r.RegionDescription"),
    (NW, "For the Beverages category, return each customer country and the total quantity of beverage products ordered by customers in that country.",
     f"SELECT cu.Country, SUM(od.Quantity) FROM Categories c JOIN Products p ON p.CategoryID = c.CategoryID JOIN {OD} od ON od.ProductID = p.ProductID JOIN Orders o ON o.OrderID = od.OrderID JOIN Customers cu ON cu.CustomerID = o.CustomerID WHERE c.CategoryName = 'Beverages' GROUP BY cu.Country"),
]

joins = lambda sql: len(re.findall(r"\bJOIN\b", sql, re.I))
nested = re.compile(r"\bSELECT\b.*\bSELECT\b|\bINTERSECT\b|\bUNION\b|\bEXCEPT\b", re.I | re.S)
agg = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(|\bGROUP\s+BY\b", re.I)

pairs = []
used = {p["question"] for p in json.load(open("eval/spider_pairs.json", encoding="utf-8"))}
for d in json.loads(zipfile.ZipFile("data/spider.zip").read("spider_data/dev.json")):
    q = d["query"]
    if joins(q) >= 2 and agg.search(q) and not nested.search(q) and d["question"] not in used:
        pairs.append({"db": f"data/spider/{d['db_id']}/{d['db_id']}.sqlite", "question": d["question"], "sql": q, "source": "spider_dev"})
pairs += [{"db": db, "question": q, "sql": s, "source": "hand"} for db, q, s in HAND]

for p in pairs:  # every gold query must run and return rows; LIMIT queries must not cut through a tie
    con = sqlite3.connect(f"file:{p['db']}?mode=ro", uri=True)
    t0 = time.perf_counter()
    rows = con.execute(p["sql"]).fetchall()
    p["joins"], ms = joins(p["sql"]), (time.perf_counter() - t0) * 1000
    assert rows, f"gold returns no rows: {p['question']}"
    if re.search(r"\bLIMIT\s+(\d+)", p["sql"], re.I):
        n = int(re.search(r"\bLIMIT\s+(\d+)", p["sql"], re.I).group(1))
        more = con.execute(re.sub(r"\bLIMIT\s+\d+", f"LIMIT {n + 1}", p["sql"], flags=re.I)).fetchall()
        assert len(more) <= n or more[n][-1] != more[n - 1][-1], f"tie at the LIMIT: {p['question']}"
    print(f"{p['source']:<10} joins={p['joins']} rows={len(rows):<4} {ms:6.0f} ms  {p['question'][:70]}")
json.dump(pairs, open("eval/hard_pairs.json", "w", encoding="utf-8"), indent=1)
print(f"\n{len(pairs)} pairs -> eval/hard_pairs.json; by joins:",
      {j: sum(p["joins"] == j for p in pairs) for j in sorted({p["joins"] for p in pairs})})
