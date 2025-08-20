import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
from neo4j import GraphDatabase
import base64
from io import BytesIO

class GenealogyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Family Tree - Genealogy Application")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Neo4j connection (update with your credentials)
        self.driver = None
        self.connect_to_neo4j()
        
        # Setup UI
        self.setup_styles()
        self.create_widgets()
        self.load_family_tree()
    
    def connect_to_neo4j(self):
        """Connect to Neo4j database"""
        try:
            # Default local Neo4j connection
            uri = "bolt://localhost:7687"
            user = "neo4j"
            password = "password"  # Change this to your Neo4j password
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            
            # Test connection and create constraints
            with self.driver.session() as session:
                # Create unique constraint on person ID
                session.run("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
                
            print("Connected to Neo4j successfully!")
            
        except Exception as e:
            messagebox.showerror("Database Connection Error", 
                               f"Could not connect to Neo4j database.\n\nError: {str(e)}\n\n" +
                               "Please ensure Neo4j is running and credentials are correct.")
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#f0f0f0')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#f0f0f0')
    
    def create_widgets(self):
        """Create the main UI components"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Family Tree Management", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Left panel for controls
        left_panel = ttk.LabelFrame(main_frame, text="Family Members", padding="10")
        left_panel.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)
        
        # Add person button
        add_btn = ttk.Button(left_panel, text="Add New Person", 
                            command=self.add_person_dialog, style='Action.TButton')
        add_btn.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Family tree list
        self.tree = ttk.Treeview(left_panel, columns=('Name', 'Address'), show='tree headings')
        self.tree.heading('#0', text='ID')
        self.tree.heading('Name', text='Full Name')
        self.tree.heading('Address', text='Address')
        self.tree.column('#0', width=50)
        self.tree.column('Name', width=150)
        self.tree.column('Address', width=200)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(left_panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=tree_scroll.set)
        
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Bind tree selection
        self.tree.bind('<<TreeviewSelect>>', self.on_person_select)
        
        # Right panel for person details
        right_panel = ttk.LabelFrame(main_frame, text="Person Details", padding="10")
        right_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(1, weight=1)
        
        # Photo display
        self.photo_label = ttk.Label(right_panel, text="No Photo", relief='sunken', width=20)
        self.photo_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Person info labels
        ttk.Label(right_panel, text="First Name:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=2)
        self.first_name_var = tk.StringVar()
        first_name_entry = ttk.Entry(right_panel, textvariable=self.first_name_var, state='readonly')
        first_name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        ttk.Label(right_panel, text="Last Name:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=2)
        self.last_name_var = tk.StringVar()
        last_name_entry = ttk.Entry(right_panel, textvariable=self.last_name_var, state='readonly')
        last_name_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        ttk.Label(right_panel, text="Address:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, pady=2)
        self.address_var = tk.StringVar()
        address_entry = ttk.Entry(right_panel, textvariable=self.address_var, state='readonly')
        address_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        # Action buttons
        button_frame = ttk.Frame(right_panel)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="Edit Person", 
                  command=self.edit_person).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Add Relationship", 
                  command=self.add_relationship_dialog).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Delete Person", 
                  command=self.delete_person).grid(row=0, column=2, padx=5)
        
        # Relationships section
        ttk.Label(right_panel, text="Relationships:", style='Header.TLabel').grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(20, 5))
        
        self.relationships_listbox = tk.Listbox(right_panel, height=6)
        self.relationships_listbox.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Current selection
        self.selected_person_id = None
    
    def load_family_tree(self):
        """Load all persons from Neo4j and populate the tree"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Person) 
                    RETURN p.id as id, p.first_name as first_name, 
                           p.last_name as last_name, p.address as address
                    ORDER BY p.last_name, p.first_name
                """)
                
                # Clear existing items
                self.tree.delete(*self.tree.get_children())
                
                for record in result:
                    person_id = record['id']
                    full_name = f"{record['first_name']} {record['last_name']}"
                    address = record['address'] or ""
                    
                    self.tree.insert('', tk.END, iid=person_id, text=person_id,
                                   values=(full_name, address))
                                   
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load family tree: {str(e)}")
    
    def on_person_select(self, event):
        """Handle person selection in tree"""
        selection = self.tree.selection()
        if not selection:
            return
            
        person_id = selection[0]
        self.selected_person_id = person_id
        self.load_person_details(person_id)
    
    def load_person_details(self, person_id):
        """Load detailed information for selected person"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                # Get person details
                result = session.run("""
                    MATCH (p:Person {id: $person_id})
                    RETURN p.first_name as first_name, p.last_name as last_name,
                           p.address as address, p.image as image
                """, person_id=person_id)
                
                record = result.single()
                if record:
                    self.first_name_var.set(record['first_name'])
                    self.last_name_var.set(record['last_name'])
                    self.address_var.set(record['address'] or "")
                    
                    # Load image if available
                    if record['image']:
                        self.load_person_image(record['image'])
                    else:
                        self.photo_label.configure(image='', text="No Photo")
                
                # Get relationships
                self.load_relationships(person_id)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load person details: {str(e)}")
    
    def load_person_image(self, image_data):
        """Load and display person's image"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Resize image to fit
            image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.photo_label.configure(image=photo, text="")
            self.photo_label.image = photo  # Keep a reference
            
        except Exception as e:
            print(f"Error loading image: {e}")
            self.photo_label.configure(image='', text="Image Error")
    
    def load_relationships(self, person_id):
        """Load relationships for selected person"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Person {id: $person_id})-[r]->(other:Person)
                    RETURN type(r) as relationship, other.first_name as first_name,
                           other.last_name as last_name, other.id as other_id
                    UNION
                    MATCH (p:Person {id: $person_id})<-[r]-(other:Person)
                    RETURN type(r) + '_OF' as relationship, other.first_name as first_name,
                           other.last_name as last_name, other.id as other_id
                """, person_id=person_id)
                
                # Clear and populate relationships listbox
                self.relationships_listbox.delete(0, tk.END)
                
                for record in result:
                    rel_type = record['relationship'].replace('_OF', ' of')
                    other_name = f"{record['first_name']} {record['last_name']}"
                    rel_text = f"{rel_type}: {other_name}"
                    self.relationships_listbox.insert(tk.END, rel_text)
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load relationships: {str(e)}")
    
    def add_person_dialog(self):
        """Show dialog to add new person"""
        dialog = PersonDialog(self.root, "Add New Person")
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.save_person(dialog.result)
    
    def edit_person(self):
        """Edit selected person"""
        if not self.selected_person_id:
            messagebox.showwarning("Warning", "Please select a person to edit.")
            return
            
        # Get current person data
        current_data = {
            'first_name': self.first_name_var.get(),
            'last_name': self.last_name_var.get(),
            'address': self.address_var.get()
        }
        
        dialog = PersonDialog(self.root, "Edit Person", current_data)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            dialog.result['id'] = self.selected_person_id
            self.save_person(dialog.result, is_edit=True)
    
    def save_person(self, person_data, is_edit=False):
        """Save person to Neo4j database"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                if is_edit:
                    # Update existing person
                    query = """
                        MATCH (p:Person {id: $id})
                        SET p.first_name = $first_name,
                            p.last_name = $last_name,
                            p.address = $address
                    """
                    if 'image' in person_data:
                        query += ", p.image = $image"
                else:
                    # Create new person
                    person_id = self.generate_person_id()
                    person_data['id'] = person_id
                    
                    query = """
                        CREATE (p:Person {
                            id: $id,
                            first_name: $first_name,
                            last_name: $last_name,
                            address: $address
                        })
                    """
                    if 'image' in person_data:
                        query = query.replace("}", ", image: $image}")
                
                session.run(query, **person_data)
                
            # Refresh the tree
            self.load_family_tree()
            messagebox.showinfo("Success", "Person saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save person: {str(e)}")
    
    def generate_person_id(self):
        """Generate unique person ID"""
        if not self.driver:
            return "P001"
            
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (p:Person) RETURN COUNT(p) as count")
                count = result.single()['count']
                return f"P{count + 1:03d}"
        except:
            return "P001"
    
    def add_relationship_dialog(self):
        """Show dialog to add relationship"""
        if not self.selected_person_id:
            messagebox.showwarning("Warning", "Please select a person first.")
            return
            
        dialog = RelationshipDialog(self.root, self.driver, self.selected_person_id)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.save_relationship(dialog.result)
    
    def save_relationship(self, rel_data):
        """Save relationship to Neo4j"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                query = f"""
                    MATCH (p1:Person {{id: $from_id}}), (p2:Person {{id: $to_id}})
                    CREATE (p1)-[:{rel_data['relationship']}]->(p2)
                """
                session.run(query, from_id=rel_data['from_id'], to_id=rel_data['to_id'])
                
            # Refresh relationships
            self.load_relationships(self.selected_person_id)
            messagebox.showinfo("Success", "Relationship added successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add relationship: {str(e)}")
    
    def delete_person(self):
        """Delete selected person"""
        if not self.selected_person_id:
            messagebox.showwarning("Warning", "Please select a person to delete.")
            return
            
        name = f"{self.first_name_var.get()} {self.last_name_var.get()}"
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {name}?"):
            try:
                with self.driver.session() as session:
                    # Delete person and all relationships
                    session.run("""
                        MATCH (p:Person {id: $person_id})
                        DETACH DELETE p
                    """, person_id=self.selected_person_id)
                    
                self.load_family_tree()
                self.clear_person_details()
                messagebox.showinfo("Success", "Person deleted successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete person: {str(e)}")
    
    def clear_person_details(self):
        """Clear person details display"""
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.address_var.set("")
        self.photo_label.configure(image='', text="No Photo")
        self.relationships_listbox.delete(0, tk.END)
        self.selected_person_id = None
    
    def __del__(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()


class PersonDialog:
    def __init__(self, parent, title, person_data=None):
        self.result = None
        self.image_data = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Create form
        self.create_form(person_data or {})
    
    def create_form(self, person_data):
        """Create person input form"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # First name
        ttk.Label(main_frame, text="First Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.first_name_var = tk.StringVar(value=person_data.get('first_name', ''))
        ttk.Entry(main_frame, textvariable=self.first_name_var, width=30).grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # Last name
        ttk.Label(main_frame, text="Last Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.last_name_var = tk.StringVar(value=person_data.get('last_name', ''))
        ttk.Entry(main_frame, textvariable=self.last_name_var, width=30).grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Address
        ttk.Label(main_frame, text="Address:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.address_var = tk.StringVar(value=person_data.get('address', ''))
        ttk.Entry(main_frame, textvariable=self.address_var, width=30).grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # Image selection
        ttk.Label(main_frame, text="Photo:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="Choose Image", command=self.choose_image).grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
    
    def choose_image(self):
        """Choose image file"""
        filename = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        
        if filename:
            try:
                # Convert image to base64
                with open(filename, "rb") as image_file:
                    self.image_data = base64.b64encode(image_file.read()).decode('utf-8')
                messagebox.showinfo("Success", "Image selected successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def save(self):
        """Save person data"""
        first_name = self.first_name_var.get().strip()
        last_name = self.last_name_var.get().strip()
        
        if not first_name or not last_name:
            messagebox.showerror("Error", "First name and last name are required!")
            return
        
        self.result = {
            'first_name': first_name,
            'last_name': last_name,
            'address': self.address_var.get().strip()
        }
        
        if self.image_data:
            self.result['image'] = self.image_data
        
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()


class RelationshipDialog:
    def __init__(self, parent, driver, person_id):
        self.result = None
        self.driver = driver
        self.person_id = person_id
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Relationship")
        self.dialog.geometry("350x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_form()
    
    def create_form(self):
        """Create relationship form"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Relationship type
        ttk.Label(main_frame, text="Relationship Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.relationship_var = tk.StringVar()
        relationship_combo = ttk.Combobox(main_frame, textvariable=self.relationship_var, width=25)
        relationship_combo['values'] = ('PARENT', 'CHILD', 'SPOUSE', 'SIBLING', 'GRANDPARENT', 'GRANDCHILD')
        relationship_combo.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # Target person
        ttk.Label(main_frame, text="Related to:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(main_frame, textvariable=self.target_var, width=25)
        self.load_persons()
        self.target_combo.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Add", command=self.add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
    
    def load_persons(self):
        """Load available persons for relationship"""
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Person) 
                    WHERE p.id <> $person_id
                    RETURN p.id as id, p.first_name as first_name, p.last_name as last_name
                    ORDER BY p.last_name, p.first_name
                """, person_id=self.person_id)
                
                persons = []
                self.person_map = {}
                
                for record in result:
                    person_id = record['id']
                    full_name = f"{record['first_name']} {record['last_name']}"
                    persons.append(full_name)
                    self.person_map[full_name] = person_id
                
                self.target_combo['values'] = persons
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load persons: {str(e)}")
    
    def add(self):
        """Add relationship"""
        relationship = self.relationship_var.get()
        target_name = self.target_var.get()
        
        if not relationship or not target_name:
            messagebox.showerror("Error", "Please select both relationship type and target person!")
            return
        
        if target_name not in self.person_map:
            messagebox.showerror("Error", "Invalid target person selected!")
            return
        
        self.result = {
            'from_id': self.person_id,
            'to_id': self.person_map[target_name],
            'relationship': relationship
        }
        
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = GenealogyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
