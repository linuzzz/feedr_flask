CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE "categories" (
    "cat" INTEGER NOT NULL,
    "description" TEXT NOT NULL
);
CREATE TABLE items2 (
	"id" INTEGER PRIMARY KEY,
    "sourceid" INTEGER,
    "title" TEXT,
    "summary" TEXT,
    "content" TEXT,
    "datetime" TEXT,
    "favorite" BOOLEAN,
    "read" INTEGER,
    "url" TEXT
);
CREATE TABLE items (
    "id" INTEGER PRIMARY KEY,
    "sourceid" INTEGER,
    "title" TEXT,
    "summary" TEXT,
    "content" TEXT,
    "favorite" BOOLEAN,
    "read" INTEGER,
    "url" TEXT,
    "pubdate" TEXT
);
CREATE TABLE sources (
    "cat" INTEGER NOT NULL,
    "sourceid" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "etag" TEXT NOT NULL DEFAULT '',
    "url" TEXT NOT NULL
, "modified" TEXT NOT NULL DEFAULT '');
