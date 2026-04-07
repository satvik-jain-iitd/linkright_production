pub fn run(stream: &str, role: Option<&str>) {
    println!("truss log {}{}", stream, role.map(|r| format!(" --role {}", r)).unwrap_or_default());
    println!("Not yet implemented — Phase 4");
}
