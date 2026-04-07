pub fn run(run_id: Option<&str>) {
    println!("truss inspect{}", run_id.map(|r| format!(" --run {}", r)).unwrap_or_default());
    println!("Not yet implemented — Phase 4");
}
