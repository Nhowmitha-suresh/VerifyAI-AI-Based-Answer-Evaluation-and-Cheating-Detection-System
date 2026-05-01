import React, { useEffect, useState } from "react"

export default function HomePage({ onStart }) {
  const [glow, setGlow] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setGlow(g => !g)
    }, 1200)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      height: "100vh",
      background: "radial-gradient(circle at top, #0f172a, #020617)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      color: "white",
      fontFamily: "Inter, sans-serif"
    }}>

      {/* Glass Card */}
      <div style={{
        backdropFilter: "blur(20px)",
        background: "rgba(255,255,255,0.05)",
        borderRadius: "20px",
        padding: "50px",
        textAlign: "center",
        boxShadow: "0 0 40px rgba(99,102,241,0.3)",
        border: "1px solid rgba(255,255,255,0.1)"
      }}>

        {/* LOGO */}
        <h1 style={{
          fontSize: "48px",
          marginBottom: "10px",
          letterSpacing: "2px"
        }}>
          verif<span style={{ color: "#818cf8" }}>AI</span>
        </h1>

        {/* TAGLINE */}
        <p style={{
          opacity: 0.7,
          marginBottom: "30px"
        }}>
          Redefining AI Interview Intelligence
        </p>

        {/* GLOWING ORB */}
        <div style={{
          margin: "30px auto",
          width: "140px",
          height: "140px",
          borderRadius: "50%",
          background: "radial-gradient(circle, #6366f1, #1e1b4b)",
          boxShadow: glow
            ? "0 0 80px #6366f1"
            : "0 0 30px #6366f1",
          transition: "all 0.8s ease-in-out"
        }} />

        {/* BUTTON */}
        <button
          onClick={onStart}
          style={{
            marginTop: "20px",
            padding: "14px 35px",
            borderRadius: "12px",
            border: "none",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            color: "white",
            fontSize: "16px",
            cursor: "pointer",
            boxShadow: "0 0 25px rgba(139,92,246,0.5)",
            transition: "0.3s"
          }}
          onMouseOver={e => e.target.style.transform = "scale(1.05)"}
          onMouseOut={e => e.target.style.transform = "scale(1)"}
        >
          Start Interview 🚀
        </button>

      </div>
    </div>
  )
}
