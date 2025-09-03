#!/usr/bin/env python3
"""
Development Environment Reset Script for OpeningBell Backend

This script will:
1. Stop and remove Docker containers and volumes
2. Spin up fresh containers
3. Create database tables
4. Load a limited set of companies (5) for testing
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def run_command(command, description, check=True):
    """Run a shell command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def wait_for_service(service_name, max_attempts=30):
    """Wait for a service to be ready"""
    print(f"\n⏳ Waiting for {service_name} to be ready...")
    
    for attempt in range(max_attempts):
        try:
            if service_name == "postgres":
                # Test PostgreSQL connection
                result = subprocess.run(
                    "docker exec opening_bell_postgres pg_isready -U postgres",
                    shell=True, capture_output=True, text=True
                )
                if result.returncode == 0:
                    print(f"✅ {service_name} is ready!")
                    return True
            elif service_name == "redis":
                # Test Redis connection
                result = subprocess.run(
                    "docker exec opening_bell_redis redis-cli ping",
                    shell=True, capture_output=True, text=True
                )
                if result.returncode == 0 and "PONG" in result.stdout:
                    print(f"✅ {service_name} is ready!")
                    return True
            
            print(f"   Attempt {attempt + 1}/{max_attempts}...")
            time.sleep(2)
            
        except Exception as e:
            print(f"   Attempt {attempt + 1}/{max_attempts} failed: {e}")
            time.sleep(2)
    
    print(f"❌ {service_name} failed to start within {max_attempts * 2} seconds")
    return False

def main():
    """Main reset process"""
    print("🚀 OpeningBell Backend - Development Environment Reset")
    print("=" * 60)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"📁 Working directory: {project_root}")
    
    # Step 1: Stop and remove containers and volumes
    print("\n" + "=" * 60)
    print("STEP 1: Cleaning up existing containers and volumes")
    print("=" * 60)
    
    run_command("docker-compose down -v", "Stopping containers and removing volumes")
    run_command("docker system prune -f", "Cleaning up Docker system")
    
    # Step 2: Spin up fresh containers
    print("\n" + "=" * 60)
    print("STEP 2: Starting fresh containers")
    print("=" * 60)
    
    run_command("docker-compose up -d", "Starting containers in detached mode")
    
    # Step 3: Wait for services to be ready
    print("\n" + "=" * 60)
    print("STEP 3: Waiting for services to be ready")
    print("=" * 60)
    
    if not wait_for_service("postgres"):
        print("❌ PostgreSQL failed to start. Exiting.")
        sys.exit(1)
    
    if not wait_for_service("redis"):
        print("❌ Redis failed to start. Exiting.")
        sys.exit(1)
    
    # Step 4: Create database tables
    print("\n" + "=" * 60)
    print("STEP 4: Creating database tables")
    print("=" * 60)
    
    run_command("python create_tables.py", "Creating database tables")
    
    # Step 5: Load companies with limit
    print("\n" + "=" * 60)
    print("STEP 5: Loading companies (limited to 5)")
    print("=" * 60)
    
    # Load companies with limit
    load_companies_script = project_root / "load_companies.py"
    if load_companies_script.exists():
        run_command("python load_companies.py --source sec --limit 5", "Loading 5 companies from SEC API")
    else:
        print("❌ load_companies.py not found")
        sys.exit(1)
    
    # Step 6: Verify setup
    print("\n" + "=" * 60)
    print("STEP 6: Verifying setup")
    print("=" * 60)
    
    # Check if containers are running
    result = run_command("docker-compose ps", "Checking container status", check=False)
    if result.returncode == 0:
        print("✅ Containers are running:")
        print(result.stdout)
    
    # Check database connection
    try:
        result = subprocess.run(
            "docker exec opening-bell-backend-postgres-1 psql -U postgres -d openingbell -c 'SELECT COUNT(*) FROM company;'",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Database connection successful")
            print(f"   Companies in database: {result.stdout.strip()}")
        else:
            print("❌ Database connection failed")
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Development environment reset complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the worker: python start_worker.py")
    print("2. Start the API server: uvicorn app.main:app --reload")
    print("3. Test financial data extraction with a sample filing")
    print("\nHappy coding! 🚀")

if __name__ == "__main__":
    main()
