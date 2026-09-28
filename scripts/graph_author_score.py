"""Human readability score for generated Designer graphs."""
def score(metrics):
    s=100
    s-=min(metrics.get("overlap",0)*5,20)
    s-=min(metrics.get("crossing",0)*2,20)
    s-=min(metrics.get("lane_violation",0)*5,20)
    s-=min(metrics.get("dead_nodes",0)*3,15)
    return max(0,s)
