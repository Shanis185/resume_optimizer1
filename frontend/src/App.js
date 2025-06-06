import React, { useState } from "react";
import axios from "axios";
import { Pie, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
} from "chart.js";
import "./App.css";

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

function App() {
  const [file, setFile] = useState(null);
  const [previewURL, setPreviewURL] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  // Handle file selection
  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      // Create a blob URL for PDF preview
      setPreviewURL(URL.createObjectURL(selected));
      setAnalysis(null);
    } else {
      alert("Please select a PDF file");
    }
  };

  // Send resume to backend for analysis
  const handleAnalyze = async () => {
    if (!file) {
      alert("Please upload a PDF resume first");
      return;
    }

    setLoading(true);
    setAnalysis(null);

    const formData = new FormData();
    formData.append("resume", file);

    try {
      const { data } = await axios.post("http://localhost:5000/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAnalysis(data);
    } catch (err) {
      console.error("Analysis error:", err);
      alert("Error analyzing resume. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  // Prepare pie chart data for ATS Score
  const pieData = analysis
    ? {
        labels: ["Matched (%)", "Remaining (%)"],
        datasets: [
          {
            data: [analysis.ats_score, 100 - analysis.ats_score],
            backgroundColor: ["#4caf50", "#f44336"],
            hoverOffset: 4,
          },
        ],
      }
    : null;

  // Prepare bar chart data for keyword counts per section
  const barData = analysis
    ? {
        labels: Object.keys(analysis.sections),
        datasets: [
          {
            label: "Keywords Matched",
            data: Object.values(analysis.sections).map((arr) => arr.length),
            backgroundColor: "#42a5f5",
          },
        ],
      }
    : null;

  return (
    <div className="container">
      <h1>🎯 AI Resume Analyzer</h1>

      <div className="upload-box">
        <label className="upload-label">
          {file ? file.name : "Click to Select PDF Resume"}
          <input type="file" accept=".pdf" onChange={handleFileChange} />
        </label>
        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze Resume"}
        </button>
      </div>

      {previewURL && (
        <iframe
          title="PDF Preview"
          className="pdf-preview"
          src={previewURL}
        ></iframe>
      )}

      {loading && (
        <div className="card">
          <h3>Analyzing… Please wait.</h3>
        </div>
      )}

      {analysis && (
        <>
          {/* ATS Score Card */}
          <div className="card">
            <h3>🥇 ATS Score: {analysis.ats_score}%</h3>
            <div className="chart-container">
              <Pie data={pieData} />
            </div>
          </div>

          {/* Keyword Counts Bar Chart */}
          <div className="card">
            <h3>🔍 Keywords Matched by Section</h3>
            <div className="chart-container">
              <Bar
                data={barData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { display: false },
                    title: {
                      display: true,
                      text: "Keywords per Section",
                      font: { size: 16 },
                    },
                  },
                }}
              />
            </div>
          </div>

          {/* AI Feedback */}
          <div className="feedback">
            <h3>🧠 AI Feedback & Suggestions</h3>
            <p>{analysis.ai_feedback}</p>
          </div>

          {/* Extracted Keywords List */}
          <div className="card">
            <h3>📑 Extracted Keywords</h3>
            {Object.entries(analysis.sections).map(([section, keywords]) => (
              <div key={section} style={{ marginBottom: "12px" }}>
                <strong>{section}:</strong>{" "}
                {keywords.length ? keywords.join(", ") : "None"}
              </div>
            ))}
          </div>

          {/* Job Match (if provided) */}
          {analysis.match_score !== undefined && (
            <div className="card">
              <h3>🧩 Match with Job Description: {analysis.match_score}%</h3>
              <p>{analysis.comparison_summary}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;
