import { useState, useEffect } from "react";
import { API_CONFIG } from "../config";

export function ConceptSelector({ 
  classGrade, 
  subject, 
  selectedConcept, 
  onConceptChange, 
  disabled = false 
}) {
  const [concepts, setConcepts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch concepts when class or subject changes
  useEffect(() => {
    if (!classGrade || !subject) {
      setConcepts([]);
      return;
    }

    const fetchConcepts = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const url = `${API_CONFIG.backendBase}${API_CONFIG.endpoints.concepts}?class_grade=${classGrade}&subject=${encodeURIComponent(subject)}`;
        const response = await fetch(url, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
          mode: 'cors',
          credentials: 'same-origin'
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch concepts: ${response.statusText}`);
        }

        const data = await response.json();
        setConcepts(data);
        
        // Auto-select first concept if none selected and concepts are available
        if (data.length > 0 && !selectedConcept) {
          onConceptChange(data[0].title);
        }
      } catch (err) {
        console.error("Error fetching concepts:", err);
        setError(err.message);
        setConcepts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchConcepts();
  }, [classGrade, subject, selectedConcept, onConceptChange]);

  // Reset selected concept when class or subject changes
  useEffect(() => {
    if (selectedConcept && concepts.length > 0) {
      const conceptExists = concepts.some(c => c.title === selectedConcept);
      if (!conceptExists) {
        onConceptChange("");
      }
    }
  }, [concepts, selectedConcept, onConceptChange]);

  if (loading) {
    return (
      <div className="input-field flex items-center gap-2">
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm text-gray-500">Loading concepts...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="input-field text-red-600 text-sm">
        Error loading concepts: {error}
      </div>
    );
  }

  if (!classGrade || !subject) {
    return (
      <select 
        className="input-field" 
        disabled 
        value=""
      >
        <option value="">Select class and subject first</option>
      </select>
    );
  }

  if (concepts.length === 0) {
    return (
      <select 
        className="input-field" 
        disabled 
        value=""
      >
        <option value="">No concepts available</option>
      </select>
    );
  }

  return (
    <select
      className="input-field"
      value={selectedConcept}
      onChange={(e) => onConceptChange(e.target.value)}
      disabled={disabled}
    >
      <option value="">Select a concept...</option>
      {concepts.map((concept) => (
        <option key={concept.id} value={concept.title}>
          {concept.title}
        </option>
      ))}
    </select>
  );
}
