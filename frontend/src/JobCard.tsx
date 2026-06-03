import React from 'react';

interface Job {
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  source: string;
}

const JobCard: React.FC<{ job: Job }> = ({ job }) => {
  // Determine badge color based on source
  let badgeColor = "bg-slate-700 text-slate-300";
  if (job.source.toLowerCase().includes("jobspy")) {
    badgeColor = "bg-indigo-900/50 text-indigo-300 border-indigo-700/50";
  } else if (job.source.toLowerCase().includes("playwright")) {
    badgeColor = "bg-blue-900/50 text-blue-300 border-blue-700/50";
  } else if (job.source.toLowerCase().includes("mcp")) {
    badgeColor = "bg-emerald-900/50 text-emerald-300 border-emerald-700/50";
  }

  return (
    <div className="bg-slate-800/80 backdrop-blur-sm border border-slate-700 rounded-xl p-5 hover:border-slate-500 hover:shadow-lg transition-all duration-300 group flex flex-col justify-between mb-4">
      <div>
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-bold text-slate-100 group-hover:text-blue-400 transition-colors">
            {job.title}
          </h3>
          <span className={`text-xs px-2.5 py-1 rounded-full border ${badgeColor}`}>
            {job.source}
          </span>
        </div>
        
        <div className="flex items-center space-x-2 text-sm text-slate-400 mb-4">
          <span className="font-semibold text-slate-300">{job.company}</span>
          <span>•</span>
          <span className="flex items-center">
            <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            {job.location}
          </span>
        </div>
        
        <p className="text-sm text-slate-500 mb-4 line-clamp-3">
          {job.description}
        </p>
      </div>

      <a 
        href={job.url !== "N/A" ? job.url : "#"} 
        target="_blank" 
        rel="noopener noreferrer"
        className={`w-full py-2.5 rounded-lg text-center font-medium transition-colors ${
          job.url !== "N/A" 
            ? "bg-blue-600 hover:bg-blue-500 text-white shadow-sm" 
            : "bg-slate-700 text-slate-400 cursor-not-allowed"
        }`}
        onClick={(e) => {
          if (job.url === "N/A") e.preventDefault();
        }}
      >
        {job.url !== "N/A" ? "Apply Now" : "Link Unavailable"}
      </a>
    </div>
  );
};

export default JobCard;
