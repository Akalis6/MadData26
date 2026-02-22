import express from "express";
import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
app.use(cors());

// If using ES modules, recreate __dirname:
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Serve the folder that contains your CSV
app.use("/data", express.static(path.join(__dirname, "data")));

// Example: http://localhost:8000/data/uwmadison_courses.csv
app.listen(8000, () => console.log("Backend running on http://localhost:8000"));