import requests
from bs4 import BeautifulSoup
import json
from rich.console import Console
from rich.table import Table
from fake_useragent import UserAgent
from rich.panel import Panel

console = Console()
ua = UserAgent()

menu = {
    "1": "View Profile",
    "2": "View Listings",
    "3": "Sign Up for a Listing",
    "4": "Withdraw from a Listing",
    "5":"Find Listing by Teacher Name",
    "6":"Logout",
    "7": "Change Password",
    "8": "Exit"
}

profileUrl = "https://teachertools.us/pdhsallin/getProfile.php"
studentInfoUrl = "https://teachertools.us/pdhsallin/student.php"
listingsUrl = "https://teachertools.us/pdhsallin/getListings.php"
loginUrl = "https://teachertools.us/pdhsallin/user_exists.php"

# ---- LOGIN ----

def login():
    global session, username, headers
    session = requests.Session()
    console.print("[bold blue]Welcome![/bold blue]")
    username = console.input("[bold green]Enter your username: [/bold green]")
    password = console.input("[bold green]Enter your password: [/bold green]", password=True)
    
    payload = {"inputUname": username, "inputPassword": password}

    headers = {"User-Agent": ua.random}
    response = session.post(loginUrl, data=payload, headers=headers)

    if response.text.strip() == "2":
        console.print("[bold green]Logged in successfully![/bold green]")
    else:
        console.print(f"[bold red]Login failed! Server returned: {response.text}[/bold red]")
        return login()  # retry login if failed

# Initial login
login()

# ---- FUNCTIONS ----
def view_profile():
    profile_info = session.get(profileUrl, headers=headers)
    soup = BeautifulSoup(profile_info.text, "lxml")

    badges_div = soup.find("div", id="badges")
    if not badges_div:
        console.print("[red]Profile info not found (possibly JS-loaded)[/red]")
        return

    name = badges_div.find("div").text.strip()
    points = badges_div.find_all("div")[4].text.strip()
    scholar_badge = "None"
    for div in badges_div.find_all("div"):
        text = div.get_text(strip=True)
        if "Scholar" in text:
            scholar_badge = text
            break

    office_blocks = soup.find_all("div", style=lambda x: x and "border-radius:.25rem" in x)
    tuesday_desc, thursday_desc = "N/A", "N/A"
    for block in office_blocks:
        h6 = block.find("h6")
        day_title = h6.text.strip() if h6 else "N/A"
        desc_div = h6.find_parent("div", class_="lh-100").find_parent("div").find_next_sibling("div")
        description = desc_div.text.strip() if desc_div else "No description found"
        if "Tuesday" in day_title:
            tuesday_desc = description
        elif "Thursday" in day_title:
            thursday_desc = description

    table = Table(title="Profile", style="bold blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Points", style="magenta")
    table.add_column("Scholar Badge", style="green")
    table.add_column("Tuesday Office Hours", style="yellow")
    table.add_column("Thursday Office Hours", style="yellow")

    table.add_row(name, points, scholar_badge, tuesday_desc, thursday_desc)
    console.print(table)


def refresh_listings():
    listings_response = session.get(listingsUrl, headers=headers)
    listings = listings_response.json()
    with open("listings.json", "w") as f:
        json.dump(listings, f, indent=4)


def view_listings():
    # Fetch the latest listings every time
    try:
        listings_response = session.get(listingsUrl, headers=headers)
        listings_response.raise_for_status()  # check for network errors
        listings = listings_response.json()
    except Exception as e:
        console.print(f"[bold red]Failed to fetch listings: {e}[/bold red]")
        return

    # Optionally save to JSON
    with open("listings.json", "w") as f:
        json.dump(listings, f, indent=4)
        

    console.print("[bold green]Fetched latest listings from server![/bold green]\n")

    # Display each day
    for day in listings:
        sheet_name = day.get("sheetName", "N/A")
        sect_date = day.get("sectDate", "N/A")
        console.rule(f"[bold blue]{sheet_name} ({sect_date})[/bold blue]")

        for listing in day.get("data", []):
            seat_total = int(listing.get("totalSeats") or 0)
            signed_up_ppl = int(listing.get("signups") or 0)
            invited_people_count = int(listing.get("session_invites") or 0)
            signups= listing.get("session_signups")
            available_seats = listing.get("seats")
            total_seats = listing.get("totalSeats")

            info = (
                f"[cyan]Teacher:[/cyan] {listing.get('fname','')} {listing.get('lname','')}\n"
                f"[cyan]Listing ID:[/cyan] {listing.get('lid','N/A')}\n"
                f"[cyan]Location:[/cyan] {listing.get('location','N/A')}\n"
                f"[cyan]Session:[/cyan] {listing.get('session','N/A')}\n"
                f"[cyan]Invites:[/cyan] {invited_people_count}\n"
                f"[cyan]SignUps:[/cyan] {signups}\n"
                # f"[cyan]SignUps:[/cyan] {signed_up_ppl}\n"
                f"[cyan]Available Seats:[/cyan] {available_seats}/{total_seats}\n"
            )
            console.print(Panel(info, expand=True, border_style="yellow"))



def signup_listing():
    listing_id = console.input("[bold green]Enter the Listing ID to sign up for: [/bold green]")
    signup_url = "https://teachertools.us/pdhsallin/addSignup.php"
    resp = session.post(signup_url, data={"lid": listing_id}, headers=headers)
    
    if resp.text.strip() == "1":
        console.print("[bold green]Successfully signed up![/bold green]")
    else:
        console.print(f"[bold red]Failed to sign up! Try Again and check lid![/bold red]")
    
    
    
    # Refresh listings JSON
    refresh_listings()

def withdraw_listing():
    listing_id = console.input("[bold green]Enter the Listing ID to withdraw from: [/bold green]")
    withdraw_url = "https://teachertools.us/pdhsallin/removeSignup.php"
    resp = session.post(withdraw_url, data={"lid": listing_id}, headers=headers)
    if resp.text.strip() == "1":
        console.print("[bold green]Successfully withdrawn![/bold green]")
    else:
        console.print(f"[bold red]Failed to withdraw! Try Again and check LID![/bold red]")

    
    # Refresh listings JSON
    refresh_listings()


def find_listing_by_teacher():
    teacher_name = console.input("[bold green]Enter the Teacher's  name to search for: [/bold green]").lower()
    
    try:
        with open("listings.json", "r") as f:
            listings = json.load(f)
    except FileNotFoundError:
        console.print("[bold red]Listings file not found. Please view listings first to fetch data.[/bold red]")
        return

    found = False
    for day in listings:
        for listing in day.get("data", []):
            full_name = f"{listing.get('fname','')} {listing.get('lname','')}".lower()
            if teacher_name in full_name:
                found = True
                seat_total = int(listing.get("totalSeats") or 0)
                signed_up_ppl = int(listing.get("session_signups") or 0)
                invited_people_count = int(listing.get("session_invites") or 0)
                name_of_day = day.get("sheetName", "N/A")
                sect_date = day.get("sectDate", "N/A")
                available_seats = listing.get("seats")
                
                total_seats = listing.get("totalSeats")

                info = (
                    f"[cyan]Day:[/cyan] {name_of_day} ({sect_date})\n"
                    f"[cyan]Teacher:[/cyan] {listing.get('fname','')} {listing.get('lname','')}\n"
                    f"[cyan]Listing ID:[/cyan] {listing.get('lid','N/A')}\n"
                    f"[cyan]Location:[/cyan] {listing.get('location','N/A')}\n"
                    f"[cyan]Session:[/cyan] {listing.get('session','N/A')}\n"
                    f"[cyan]Invites:[/cyan] {invited_people_count}\n"
                    f"[cyan]SignUps:[/cyan] {signed_up_ppl}\n"
                    
                    # f"[cyan]SignUps:[/cyan] {signed_up_ppl}\n"
                    f"[cyan]Available Seats:[/cyan] {available_seats}/{total_seats}\n"
                )
                console.print(Panel(info, expand=True, border_style="bold red"))
    
    if not found:
        console.print(f"[bold red]No listings found for teacher: {teacher_name}[/bold red]")


def change_pw():
    change_pw_url = "https://teachertools.us/pdhsallin/changePWs.php"
    console.input("[bold red]You chose to change password. Press Enter![/bold red]")
    new_pw = console.input("[bold green]Enter your new password: [/bold green]", password=False)
    
    if new_pw.strip() == "":
        console.print("[bold red]Password cannot be empty![/bold red]")
        return
    resp = session.post(change_pw_url, data={"pw": new_pw}, headers=headers)
    if resp.text.strip() == "1":
        console.print("[bold yellow]Password changed successfully![/bold yellow]")
    else:
        console.print(f"[bold red]Failed to change password![/bold red]")
# ---- MENU LOOP ----
while True:
    console.print("\n[bold blue]Menu:[/bold blue]")
    for key, value in menu.items():
        console.print(f"[bold green]{key}.[/bold green] {value}")
    choice = console.input("[bold green]Enter your choice: [/bold green]")

    if choice == "1":
        view_profile()
    elif choice == "2":
        view_listings()
    elif choice == "3":
        signup_listing()
    elif choice == "4":
        withdraw_listing()
    elif choice == "5":
        find_listing_by_teacher()
    elif choice == "6":
        console.print("[bold green]Logging out...[/bold green]")
        session.cookies.clear()
        console.print("[bold green]Logged out successfully![/bold green]")
        login()
        
    elif choice == "7":
        change_pw()
    elif choice == "8":
        console.print("[bold red]Exiting...[/bold red]")
        break
    else:
        console.print("[bold red]Invalid choice![/bold red]")
