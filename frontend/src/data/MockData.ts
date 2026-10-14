export const dashboardData = {
  mastery: 72,
  weeklyChange: 8,
  studyHours: 6.5,
  completedAssessments: 12,

  focusAreas: [
    {
      topic: "Database Normalization",
      subject: "DBMS",
      mastery: 48,
      reason: "You struggled with 3 recent questions.",
      action: "Revise functional dependencies",
    },
    {
      topic: "Transaction Management",
      subject: "DBMS",
      mastery: 55,
      reason: "Some concepts need more practice.",
      action: "Review ACID properties",
    },
    {
      topic: "Probability Distributions",
      subject: "Mathematics",
      mastery: 63,
      reason: "Your answers show room for improvement.",
      action: "Practice distribution problems",
    },
  ],

  recommendations: [
    {
      title: "Review Database Normalization",
      description: "Revisit functional dependencies and normal forms.",
      duration: "20 min",
      type: "Revision",
    },
    {
      title: "Try a focused assessment",
      description: "Practice questions about transaction management.",
      duration: "10 min",
      type: "Practice",
    },
  ],

  weeklyProgress: [
    { day: "Mon", value: 35 },
    { day: "Tue", value: 55 },
    { day: "Wed", value: 42 },
    { day: "Thu", value: 72 },
    { day: "Fri", value: 60 },
    { day: "Sat", value: 85 },
    { day: "Sun", value: 68 },
  ],
};