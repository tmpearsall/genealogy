
import streamlit as st
import json
import hashlib
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
import os

# Page configuration
st.set_page_config(
    page_title="🌳 Family Tree Builder",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
DB_FILE = "family_tree.db"

def init_database():
    """Initialize SQLite database with tables for users, family members, and relationships"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Family members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date DATE,
            death_date DATE,
            birth_place TEXT,
            occupation TEXT,
            notes TEXT,
            x_position REAL DEFAULT 0,
            y_position REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Relationships table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_member_id INTEGER NOT NULL,
            to_member_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT,
            is_primary BOOLEAN DEFAULT TRUE,
            linked_relationship_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (from_member_id) REFERENCES family_members (id),
            FOREIGN KEY (to_member_id) REFERENCES family_members (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def create_user(username, password, email=""):
    """Create a new user account"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists

def authenticate_user(username, password):
    """Authenticate user login"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result and verify_password(password, result[1]):
        return result[0]  # Return user ID
    return None

def get_user_family_members(user_id):
    """Get all family members for a user"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM family_members WHERE user_id = ? ORDER BY first_name, last_name",
        conn,
        params=(user_id,)
    )
    conn.close()
    return df

def get_user_relationships(user_id):
    """Get all relationships for a user"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        """
        SELECT r.*, 
               fm1.first_name as from_first_name, fm1.last_name as from_last_name,
               fm2.first_name as to_first_name, fm2.last_name as to_last_name
        FROM relationships r
        JOIN family_members fm1 ON r.from_member_id = fm1.id
        JOIN family_members fm2 ON r.to_member_id = fm2.id
        WHERE r.user_id = ?
        ORDER BY r.created_at
        """,
        conn,
        params=(user_id,)
    )
    conn.close()
    return df

def add_family_member(user_id, member_data):
    """Add a new family member"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT INTO family_members 
        (user_id, first_name, last_name, birth_date, death_date, birth_place, occupation, notes, x_position, y_position)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            member_data['first_name'],
            member_data['last_name'],
            member_data.get('birth_date'),
            member_data.get('death_date'),
            member_data.get('birth_place', ''),
            member_data.get('occupation', ''),
            member_data.get('notes', ''),
            member_data.get('x_position', 0),
            member_data.get('y_position', 0)
        )
    )
    
    member_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return member_id

def update_family_member(member_id, member_data):
    """Update existing family member"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        UPDATE family_members 
        SET first_name=?, last_name=?, birth_date=?, death_date=?, 
            birth_place=?, occupation=?, notes=?
        WHERE id=?
        """,
        (
            member_data['first_name'],
            member_data['last_name'],
            member_data.get('birth_date'),
            member_data.get('death_date'),
            member_data.get('birth_place', ''),
            member_data.get('occupation', ''),
            member_data.get('notes', ''),
            member_id
        )
    )
    
    conn.commit()
    conn.close()

def delete_family_member(user_id, member_id):
    """Delete family member and all their relationships"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Delete relationships
    cursor.execute(
        "DELETE FROM relationships WHERE user_id = ? AND (from_member_id = ? OR to_member_id = ?)",
        (user_id, member_id, member_id)
    )
    
    # Delete family member
    cursor.execute(
        "DELETE FROM family_members WHERE user_id = ? AND id = ?",
        (user_id, member_id)
    )
    
    conn.commit()
    conn.close()

def get_inverse_relationship(relationship_type):
    """Get the inverse relationship type"""
    inverse_map = {
        'spouse': 'spouse',
        'parent': 'child',
        'child': 'parent',
        'sibling': 'sibling',
        'grandparent': 'grandchild',
        'grandchild': 'grandparent',
        'aunt-uncle': 'niece-nephew',
        'niece-nephew': 'aunt-uncle',
        'cousin': 'cousin',
        'in-law': 'in-law',
        'other': 'other'
    }
    return inverse_map.get(relationship_type, 'other')

def add_relationship(user_id, from_member_id, to_member_id, relationship_type, notes=""):
    """Add bidirectional relationship"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if relationship already exists
    cursor.execute(
        """
        SELECT id FROM relationships 
        WHERE user_id = ? AND (
            (from_member_id = ? AND to_member_id = ?) OR
            (from_member_id = ? AND to_member_id = ?)
        )
        """,
        (user_id, from_member_id, to_member_id, to_member_id, from_member_id)
    )
    
    if cursor.fetchone():
        conn.close()
        return False  # Relationship already exists
    
    # Add primary relationship
    cursor.execute(
        """
        INSERT INTO relationships 
        (user_id, from_member_id, to_member_id, relationship_type, notes, is_primary)
        VALUES (?, ?, ?, ?, ?, TRUE)
        """,
        (user_id, from_member_id, to_member_id, relationship_type, notes)
    )
    
    primary_id = cursor.lastrowid
    inverse_type = get_inverse_relationship(relationship_type)
    
    # Add inverse relationship if different or for symmetric relationships
    if relationship_type != inverse_type or relationship_type in ['spouse', 'sibling', 'cousin']:
        cursor.execute(
            """
            INSERT INTO relationships 
            (user_id, from_member_id, to_member_id, relationship_type, notes, is_primary, linked_relationship_id)
            VALUES (?, ?, ?, ?, ?, FALSE, ?)
            """,
            (user_id, to_member_id, from_member_id, inverse_type, notes, primary_id)
        )
    
    conn.commit()
    conn.close()
    return True

def delete_relationship(user_id, relationship_id):
    """Delete relationship and its inverse"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get the relationship to check if it's primary
    cursor.execute(
        "SELECT is_primary, linked_relationship_id FROM relationships WHERE user_id = ? AND id = ?",
        (user_id, relationship_id)
    )
    result = cursor.fetchone()
    
    if result:
        is_primary, linked_id = result
        
        if is_primary:
            # Delete primary and its linked inverse
            cursor.execute(
                "DELETE FROM relationships WHERE user_id = ? AND (id = ? OR linked_relationship_id = ?)",
                (user_id, relationship_id, relationship_id)
            )
        else:
            # Delete inverse and its primary
            cursor.execute(
                "DELETE FROM relationships WHERE user_id = ? AND (id = ? OR id = ?)",
                (user_id, relationship_id, linked_id)
            )
    
    conn.commit()
    conn.close()

def create_family_tree_graph(user_id):
    """Create an interactive family tree graph using Plotly"""
    members_df = get_user_family_members(user_id)
    relationships_df = get_user_relationships(user_id)
    
    if members_df.empty:
        return None
    
    # Create networkx graph
    G = nx.Graph()
    
    # Add nodes
    for _, member in members_df.iterrows():
        full_name = f"{member['first_name']} {member['last_name']}"
        G.add_node(
            member['id'],
            name=full_name,
            birth_date=member.get('birth_date', ''),
            birth_place=member.get('birth_place', ''),
            occupation=member.get('occupation', '')
        )
    
    # Add edges (only primary relationships to avoid duplicates)
    primary_relationships = relationships_df[relationships_df['is_primary'] == True]
    for _, rel in primary_relationships.iterrows():
        G.add_edge(
            rel['from_member_id'],
            rel['to_member_id'],
            relationship=rel['relationship_type'],
            notes=rel.get('notes', '')
        )
    
    # Generate layout
    if len(G.nodes) > 0:
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    else:
        pos = {}
    
    # Prepare data for Plotly
    edge_x = []
    edge_y = []
    edge_info = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        
        # Get relationship info
        rel_type = edge[2].get('relationship', '')
        inverse_type = get_inverse_relationship(rel_type)
        edge_info.append(f"{rel_type} ↔ {inverse_type}")
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_info = []
    
    for node in G.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node[1]['name'])
        
        # Create hover info
        info = f"<b>{node[1]['name']}</b><br>"
        if node[1]['birth_date']:
            info += f"Born: {node[1]['birth_date']}<br>"
        if node[1]['birth_place']:
            info += f"Birth Place: {node[1]['birth_place']}<br>"
        if node[1]['occupation']:
            info += f"Occupation: {node[1]['occupation']}"
        node_info.append(info)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="middle center",
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=node_info,
        marker=dict(
            size=30,
            color='lightblue',
            line=dict(width=2, color='darkblue')
        ),
        textfont=dict(size=10, color='black')
    )
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Family Tree Relationship Graph',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Drag to pan, zoom to explore",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            xanchor='left', yanchor='bottom',
                            font=dict(color='gray', size=12)
                        )],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        plot_bgcolor='white'
                    ))
    
    return fig

# Initialize database
init_database()

# Authentication state management
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Login/Register Interface
if st.session_state.user_id is None:
    st.title("🌳 Family Tree Builder")
    st.markdown("### Welcome! Please login or create an account to continue.")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")
            
            if login_button:
                user_id = authenticate_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        st.header("Create New Account")
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_email = st.text_input("Email (optional)")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register_button = st.form_submit_button("Create Account")
            
            if register_button:
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    if create_user(new_username, new_password, new_email):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Username already exists")

# Main Application (after authentication)
else:
    # Header with logout button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"🌳 Family Tree Builder - Welcome, {st.session_state.username}!")
    with col2:
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Family Members", "Add/Edit Members", "Relationships", "Family Tree Graph", "Statistics"]
    )
    
    # Get current user's data
    user_id = st.session_state.user_id
    members_df = get_user_family_members(user_id)
    relationships_df = get_user_relationships(user_id)
    
    # Family Members Page
    if page == "Family Members":
        st.header("👥 Family Members")
        
        if not members_df.empty:
            # Search functionality
            search_term = st.text_input("🔍 Search family members", placeholder="Search by name, place, or occupation...")
            
            if search_term:
                mask = (
                    members_df['first_name'].str.contains(search_term, case=False, na=False) |
                    members_df['last_name'].str.contains(search_term, case=False, na=False) |
                    members_df['birth_place'].str.contains(search_term, case=False, na=False) |
                    members_df['occupation'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = members_df[mask]
            else:
                filtered_df = members_df
            
            # Display members
            for _, member in filtered_df.iterrows():
                with st.expander(f"👤 {member['first_name']} {member['last_name']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if member['birth_date']:
                            st.write(f"**Born:** {member['birth_date']}")
                        if member['death_date']:
                            st.write(f"**Died:** {member['death_date']}")
                        if member['birth_place']:
                            st.write(f"**Birth Place:** {member['birth_place']}")
                    
                    with col2:
                        if member['occupation']:
                            st.write(f"**Occupation:** {member['occupation']}")
                        if member['notes']:
                            st.write(f"**Notes:** {member['notes']}")
                    
                    # Show relationships
                    member_relationships = relationships_df[
                        relationships_df['from_member_id'] == member['id']
                    ]
                    
                    if not member_relationships.empty:
                        st.write("**Relationships:**")
                        for _, rel in member_relationships.iterrows():
                            relationship_text = f"{rel['relationship_type']} of {rel['to_first_name']} {rel['to_last_name']}"
                            if rel['notes']:
                                relationship_text += f" ({rel['notes']})"
                            st.write(f"• {relationship_text}")
                    
                    # Action buttons
                    col3, col4 = st.columns(2)
                    with col3:
                        if st.button(f"Edit {member['first_name']}", key=f"edit_{member['id']}"):
                            st.session_state.editing_member = member['id']
                    with col4:
                        if st.button(f"Delete {member['first_name']}", key=f"delete_{member['id']}"):
                            delete_family_member(user_id, member['id'])
                            st.success(f"Deleted {member['first_name']} {member['last_name']}")
                            st.rerun()
        else:
            st.info("No family members added yet. Use the 'Add/Edit Members' page to get started!")
    
    # Add/Edit Members Page
    elif page == "Add/Edit Members":
        st.header("➕ Add/Edit Family Members")
        
        # Check if editing
        editing_member_id = st.session_state.get('editing_member', None)
        editing_member = None
        
        if editing_member_id:
            editing_member = members_df[members_df['id'] == editing_member_id]
            if not editing_member.empty:
                editing_member = editing_member.iloc[0]
                st.info(f"Editing: {editing_member['first_name']} {editing_member['last_name']}")
        
        with st.form("member_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input(
                    "First Name *", 
                    value=editing_member['first_name'] if editing_member is not None else ""
                )
                birth_date = st.date_input(
                    "Birth Date",
                    value=pd.to_datetime(editing_member['birth_date']).date() if editing_member is not None and editing_member['birth_date'] else None
                )
                birth_place = st.text_input(
                    "Birth Place",
                    value=editing_member['birth_place'] if editing_member is not None else ""
                )
            
            with col2:
                last_name = st.text_input(
                    "Last Name *",
                    value=editing_member['last_name'] if editing_member is not None else ""
                )
                death_date = st.date_input(
                    "Death Date (if applicable)",
                    value=pd.to_datetime(editing_member['death_date']).date() if editing_member is not None and editing_member['death_date'] else None
                )
                occupation = st.text_input(
                    "Occupation",
                    value=editing_member['occupation'] if editing_member is not None else ""
                )
            
            notes = st.text_area(
                "Notes",
                value=editing_member['notes'] if editing_member is not None else ""
            )
            
            col3, col4 = st.columns(2)
            with col3:
                submit_button = st.form_submit_button("Update Member" if editing_member is not None else "Add Member")
            with col4:
                if editing_member is not None:
                    cancel_button = st.form_submit_button("Cancel Edit")
                    if cancel_button:
                        st.session_state.editing_member = None
                        st.rerun()
            
            if submit_button:
                if not first_name or not last_name:
                    st.error("First name and last name are required!")
                else:
                    member_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'birth_date': birth_date.isoformat() if birth_date else None,
                        'death_date': death_date.isoformat() if death_date else None,
                        'birth_place': birth_place,
                        'occupation': occupation,
                        'notes': notes
                    }
                    
                    if editing_member is not None:
                        update_family_member(editing_member_id, member_data)
                        st.success(f"Updated {first_name} {last_name}")
                        st.session_state.editing_member = None
                    else:
                        add_family_member(user_id, member_data)
                        st.success(f"Added {first_name} {last_name}")
                    
                    st.rerun()
    
    # Relationships Page
    elif page == "Relationships":
        st.header("🔗 Manage Relationships")
        
        if len(members_df) < 2:
            st.warning("You need at least 2 family members to create relationships.")
        else:
            st.subheader("Add New Relationship")
            
            with st.form("relationship_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    from_member = st.selectbox(
                        "Select first person",
                        options=members_df['id'].tolist(),
                        format_func=lambda x: f"{members_df[members_df['id']==x]['first_name'].iloc[0]} {members_df[members_df['id']==x]['last_name'].iloc[0]}"
                    )
                    
                    relationship_type = st.selectbox(
                        "Relationship type",
                        ["spouse", "parent", "child", "sibling", "grandparent", "grandchild", 
                         "aunt-uncle", "niece-nephew", "cousin", "in-law", "other"]
                    )
                
                with col2:
                    to_member = st.selectbox(
                        "Select second person",
                        options=[m for m in members_df['id'].tolist() if m != from_member],
                        format_func=lambda x: f"{members_df[members_df['id']==x]['first_name'].iloc[0]} {members_df[members_df['id']==x]['last_name'].iloc[0]}"
                    )
                    
                    relationship_notes = st.text_input("Relationship notes (optional)")
                
                add_relationship_button = st.form_submit_button("Add Relationship")
                
                if add_relationship_button:
                    if add_relationship(user_id, from_member, to_member, relationship_type, relationship_notes):
                        from_name = f"{members_df[members_df['id']==from_member]['first_name'].iloc[0]} {members_df[members_df['id']==from_member]['last_name'].iloc[0]}"
                        to_name = f"{members_df[members_df['id']==to_member]['first_name'].iloc[0]} {members_df[members_df['id']==to_member]['last_name'].iloc[0]}"
                        st.success(f"Added relationship: {from_name} is {relationship_type} of {to_name}")
                        st.rerun()
                    else:
                        st.error("Relationship already exists between these people!")
            
            # Display existing relationships
            st.subheader("Existing Relationships")
            
            if not relationships_df.empty:
                # Show only primary relationships to avoid duplicates
                primary_relationships = relationships_df[relationships_df['is_primary'] == True]
                
                for _, rel in primary_relationships.iterrows():
                    with st.expander(f"{rel['from_first_name']} {rel['from_last_name']} ↔ {rel['to_first_name']} {rel['to_last_name']}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**{rel['from_first_name']} {rel['from_last_name']}** is **{rel['relationship_type']}** of **{rel['to_first_name']} {rel['to_last_name']}**")
                            inverse_type = get_inverse_relationship(rel['relationship_type'])
                            st.write(f"**{rel['to_first_name']} {rel['to_last_name']}** is **{inverse_type}** of **{rel['from_first_name']} {rel['from_last_name']}**")
                            
                            if rel['notes']:
                                st.write(f"**Notes:** {rel['notes']}")
                        
                        with col2:
                            if st.button("Delete", key=f"del_rel_{rel['id']}"):
                                delete_relationship(user_id, rel['id'])
                                st.success("Relationship deleted!")
                                st.rerun()
            else:
                st.info("No relationships added yet.")
    
    # Family Tree Graph Page
    elif page == "Family Tree Graph":
        st.header("🌳 Interactive Family Tree")
        
        if not members_df.empty:
            fig = create_family_tree_graph(user_id)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True, height=600)
                
                st.info("💡 **Tips:** Hover over nodes to see details. The graph shows bidirectional relationships with arrows indicating the relationship types.")
            else:
                st.warning("Unable to generate graph. Please add family members first.")
        else:
            st.info("Add family members and relationships to see your family tree graph!")
    
    # Statistics Page
    elif page == "Statistics":
        st.header("📊 Family Tree Statistics")
        
        if not members_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Family Members", len(members_df))
            
            with col2:
                living_members = len(members_df[members_df['death_date'].isna()])
                st.metric("Living Members", living_members)
            
            with col3:
                deceased_members = len(members_df[members_df['death_date'].notna()])
                st.metric("Deceased Members", deceased_members)
            
            with col4:
                total_relationships = len(relationships_df[relationships_df['is_primary'] == True])
                st.metric("Total Relationships", total_relationships)
            
            # Birth places chart
            if not members_df['birth_place'].isna().all() and members_df['birth_place'].str.strip().ne('').any():
                st.subheader("Birth Places Distribution")
                birth_places = members_df['birth_place'].value_counts().head(10)
                
                fig_places = px.bar(
                    x=birth_places.values,
                    y=birth_places.index,
                    orientation='h',
                    title="Top Birth Places",
                    labels={'x': 'Number of Family Members', 'y': 'Birth Place'}
                )
                st.plotly_chart(fig_places, use_container_width=True)
            
            # Occupations chart
            if not members_df['occupation'].isna().all() and members_df['occupation'].str.strip().ne('').any():
                st.subheader("Occupations Distribution")
                occupations = members_df['occupation'].value_counts().head(10)
                
                fig_occupations = px.pie(
                    values=occupations.values,
                    names=occupations.index,
                    title="Family Occupations"
                )
                st.plotly_chart(fig_occupations, use_container_width=True)
            
            # Relationship types chart
            if not relationships_df.empty:
                st.subheader("Relationship Types Distribution")
                primary_rels = relationships_df[relationships_df['is_primary'] == True]
                rel_counts = primary_rels['relationship_type'].value_counts()
                
                fig_relationships = px.bar(
                    x=rel_counts.index,
                    y=rel_counts.values,
                    title="Types of Relationships in Family Tree",
                    labels={'x': 'Relationship Type', 'y': 'Count'}
                )
                fig_relationships.update_xaxis(tickangle=45)
                st.plotly_chart(fig_relationships, use_container_width=True)
            
            # Birth timeline
            birth_years = members_df[members_df['birth_date'].notna()].copy()
            if not birth_years.empty:
                birth_years['birth_year'] = pd.to_datetime(birth_years['birth_date']).dt.year
                
                st.subheader("Birth Timeline")
                fig_timeline = px.histogram(
                    birth_years,
                    x='birth_year',
                    nbins=20,
                    title="Family Members Birth Years",
                    labels={'birth_year': 'Birth Year', 'count': 'Number of Family Members'}
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Family tree generation analysis
            st.subheader("Generation Analysis")
            
            # Simple generation detection based on relationships
            generations = {}
            
            # Find people with no parents (likely oldest generation)
            parent_relationships = relationships_df[
                (relationships_df['relationship_type'] == 'parent') & 
                (relationships_df['is_primary'] == True)
            ]
            
            children_ids = set(parent_relationships['to_member_id'].tolist())
            all_member_ids = set(members_df['id'].tolist())
            root_generation = all_member_ids - children_ids
            
            if root_generation:
                st.write(f"**Oldest Generation ({len(root_generation)} members):**")
                for member_id in root_generation:
                    member = members_df[members_df['id'] == member_id].iloc[0]
                    st.write(f"• {member['first_name']} {member['last_name']}")
                
                # Find children of root generation
                children_of_root = parent_relationships[
                    parent_relationships['from_member_id'].isin(root_generation)
                ]['to_member_id'].tolist()
                
                if children_of_root:
                    st.write(f"**Next Generation ({len(children_of_root)} members):**")
                    for member_id in children_of_root:
                        member = members_df[members_df['id'] == member_id].iloc[0]
                        st.write(f"• {member['first_name']} {member['last_name']}")
        else:
            st.info("Add family members to see statistics!")
    
    # Sidebar additional features
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Management")
    
    # Export data
    if st.sidebar.button("Export Family Data"):
        if not members_df.empty or not relationships_df.empty:
            export_data = {
                'family_members': members_df.to_dict('records'),
                'relationships': relationships_df.to_dict('records'),
                'export_date': datetime.now().isoformat()
            }
            
            json_string = json.dumps(export_data, indent=2, default=str)
            st.sidebar.download_button(
                label="Download JSON",
                data=json_string,
                file_name=f"family_tree_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        else:
            st.sidebar.warning("No data to export!")
    
    # Import data
    st.sidebar.subheader("Import Data")
    uploaded_file = st.sidebar.file_uploader("Choose JSON file", type="json")
    
    if uploaded_file is not None:
        try:
            import_data = json.load(uploaded_file)
            
            if 'family_members' in import_data:
                st.sidebar.success("File loaded successfully!")
                
                if st.sidebar.button("Import Data"):
                    # This would need additional logic to handle importing
                    # without duplicate IDs and proper user association
                    st.sidebar.info("Import functionality would be implemented here")
            else:
                st.sidebar.error("Invalid file format!")
        except json.JSONDecodeError:
            st.sidebar.error("Error reading JSON file!")
    
    # Quick stats in sidebar
    if not members_df.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Quick Stats")
        st.sidebar.write(f"👥 {len(members_df)} family members")
        if not relationships_df.empty:
            primary_rels = len(relationships_df[relationships_df['is_primary'] == True])
            st.sidebar.write(f"🔗 {primary_rels} relationships")
        
        # Most common birth place
        if not members_df['birth_place'].isna().all():
            top_place = members_df['birth_place'].value_counts().index[0] if len(members_df['birth_place'].value_counts()) > 0 else "N/A"
            st.sidebar.write(f"📍 Most common birthplace: {top_place}")
        
        # Age range
        current_year = datetime.now().year
        birth_years = members_df[members_df['birth_date'].notna()].copy()
        if not birth_years.empty:
            birth_years['birth_year'] = pd.to_datetime(birth_years['birth_date']).dt.year
            oldest_year = birth_years['birth_year'].min()
            newest_year = birth_years['birth_year'].max()
            st.sidebar.write(f"📅 Birth years: {oldest_year} - {newest_year}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 14px;'>
        🌳 Family Tree Builder | Built with Streamlit | 
        Secure family history management with user authentication
    </div>
    """, 
    unsafe_allow_html=True
)

# CSS for better styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main > div {
        background: white;
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
    }
    
    .stExpander {
        border: 2px solid #e0e6ed;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
    
    .stTextInput > div > div > input {
        background-color: #f8f9fa;
    }
    
    .stTextArea > div > div > textarea {
        background-color: #f8f9fa;
    }
    
    .stDateInput > div > div > input {
        background-color: #f8f9fa;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)