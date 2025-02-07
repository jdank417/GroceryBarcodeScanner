// src/Home.js
import React, { useState } from 'react';

const Home = () => {
  const [barcode, setBarcode] = useState('');
  const [result, setResult] = useState(null);
  const [feedback, setFeedback] = useState('');

  // Handle manual barcode submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!barcode.trim()) {
      setFeedback('Please enter a valid barcode.');
      return;
    }
    try {
      const res = await fetch('/api/lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcode_id: barcode })
      });
      const data = await res.json();
      if (res.ok) {
        setResult(`Item: ${data.item_name}, Price: $${data.item_price}`);
        setFeedback('');
      } else {
        setResult(null);
        setFeedback(data.error || 'Item not found.');
      }
    } catch (error) {
      console.error(error);
      setFeedback('An error occurred during lookup.');
    }
  };

  // Simulated barcode decoding from an image
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        const dataURL = evt.target.result;
        // Simulate a successful barcode decode
        const simulatedBarcode = "123456789012"; // Replace with actual decode result from QuaggaJS or similar
        setBarcode(simulatedBarcode);
        setTimeout(() => handleSubmit(new Event('submit')), 500);
      };
      reader.readAsDataURL(file);
    }
  };

  const openNativeCamera = () => {
    document.getElementById("native-camera-input").click();
  };

  return (
    <main style={{ padding: '2rem' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Logo Section */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <img src="/static/uploads/BAC_Logo_tr.png" alt="Logo" style={{ width: '250px' }} />
        </div>
        {/* Barcode Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="barcode">Enter Barcode ID:</label>
            <input
              type="text"
              id="barcode"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              style={{ width: '100%', padding: '0.5rem' }}
              placeholder="Enter UPC here"
              required
            />
          </div>
          <button type="submit" style={{ padding: '0.5rem 1rem' }}>Submit</button>
        </form>
        {/* Camera Scan Section */}
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <p>Or scan your barcode with your camera</p>
          <button onClick={openNativeCamera} style={{ padding: '0.5rem 1rem' }}>
            Scan Barcode Using Camera
          </button>
          <input type="file" accept="image/*;capture=camera" id="native-camera-input" style={{ display: 'none' }} onChange={handleFileChange} />
        </div>
        {/* Feedback and Results */}
        {feedback && <div style={{ marginTop: '1rem', color: 'red' }}>{feedback}</div>}
        {result && <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #ccc' }}>{result}</div>}
      </div>
    </main>
  );
};

export default Home;
