require('dotenv').config();
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const port = 5000;

const storage = multer.diskStorage({
  destination: 'uploads/',
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname),
});
const upload = multer({ storage });

app.use(cors());
app.use(express.json());

app.post('/analyze', upload.single('resume'), (req, res) => {
  const filePath = path.join(__dirname, 'uploads', req.file.filename);
  const args = [filePath];
  if (req.body.jobDescription) args.push(req.body.jobDescription);

  const python = spawn('python', ['extract_text.py', ...args]);

  let output = '';
  python.stdout.on('data', (data) => (output += data.toString()));
  python.stderr.on('data', (data) => console.error(data.toString()));

  python.on('close', () => {
    try {
      res.json(JSON.parse(output));
    } catch (err) {
      res.status(500).json({ error: 'Analysis failed', details: err.message });
    }
  });
});

app.listen(port, () => console.log(`Server running at http://localhost:${port}`));
