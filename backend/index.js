require('dotenv').config();
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 5000;

// Multer storage setup
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadPath = path.join(__dirname, 'uploads');
    // Ensure the uploads directory exists
    fs.mkdirSync(uploadPath, { recursive: true });
    cb(null, uploadPath);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  },
});

const upload = multer({ storage });

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // Parse form fields in POST

// POST /analyze endpoint
app.post('/analyze', upload.single('resume'), (req, res) => {
  const filePath = path.join(__dirname, 'uploads', req.file.filename);
  const jobDescription = req.body.job_description || ""; // Ensure field name matches frontend

  // Prepare arguments for Python script
  const args = ['extract_text.py', filePath];
  if (jobDescription.trim()) {
    args.push(jobDescription);
  }

  // Spawn Python process
  const python = spawn('python', args);

  let output = '';
  python.stdout.on('data', (data) => {
    output += data.toString();
  });

  python.stderr.on('data', (data) => {
    console.error("Python error:", data.toString());
  });

  python.on('close', (code) => {
    console.log("Python script exited with code:", code);
    console.log("Python Output:\n", output);

    try {
      const result = JSON.parse(output);
      res.json(result);
    } catch (err) {
      res.status(500).json({ error: 'Analysis failed', details: err.message });
    }
  });
});

// Start server
app.listen(port, () => {
  console.log(`✅ Server running at: http://localhost:${port}`);
});
