import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import pywhatkit as kit
import threading
import os
import numpy as np
import face_recognition
from sklearn.cluster import DBSCAN
from PIL import Image, ImageTk
import traceback

class AdvancedWhatsAppBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced PyWhatKit & Face Clustering Automation Engine")
        self.root.geometry("1100x700")
        
        # Database Structure: {"Person_1": ["path/to/photo1.jpg", ...], ...}
        self.labels_data = {}
        
        # Image Gallery Tracking
        self.image_list = []  
        self.current_img_index = 0
        
        # Chatbot History Memory Tracking 
        self.chat_history = []
        self.conversation_active = True

        self.setup_ui()
        self.bind_keyboard_events()
        self.update_image_preview()

    def setup_ui(self):
        # Main Layout Separation
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # -------------------------------------------------------------
        # LEFT PANEL: People & Labels Management
        # -------------------------------------------------------------
        left_frame = tk.LabelFrame(self.main_pane, text="People & Group Labels", width=250)
        self.main_pane.add(left_frame)

        self.labels_box = tk.Listbox(left_frame, selectmode=tk.SINGLE, font=("Arial", 10))
        self.labels_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.labels_box.bind("<<ListboxSelect>>", self.on_label_select)

        btn_grid = tk.Frame(left_frame)
        btn_grid.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(btn_grid, text="Add Label", command=self.add_label, bg="#D4EDDA", font=("Arial", 9)).grid(row=0, column=0, sticky="we", padx=2, pady=2)
        tk.Button(btn_grid, text="Rename", command=self.rename_label, bg="#FFF3CD", font=("Arial", 9)).grid(row=0, column=1, sticky="we", padx=2, pady=2)
        tk.Button(btn_grid, text="Delete", command=self.delete_label, bg="#F8D7DA", font=("Arial", 9)).grid(row=0, column=2, sticky="we", padx=2, pady=2)
        tk.Button(btn_grid, text="Add Photo to Selected Label", command=self.add_photo_to_label, bg="#CCE5FF", font=("Arial", 9, "bold")).grid(row=1, column=0, columnspan=3, sticky="we", padx=2, pady=4)
        btn_grid.columnconfigure((0,1,2), weight=1)

        # -------------------------------------------------------------
        # MIDDLE PANEL: Media Gallery Viewport
        # -------------------------------------------------------------
        mid_frame = tk.LabelFrame(self.main_pane, text="Image Preview Canvas", width=450)
        self.main_pane.add(mid_frame)

        # Controls & Scan Toolbar at top of Middle Frame
        scan_toolbar = tk.Frame(mid_frame)
        scan_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_scan = tk.Button(scan_toolbar, text="📸 Scan Directory for Faces", command=self.start_directory_scan, bg="#007BFF", fg="white", font=("Arial", 10, "bold"))
        self.btn_scan.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = tk.Label(scan_toolbar, text="No directory scanned. Click button above to start clustering.", font=("Arial", 9, "italic"), fg="#555555")
        self.status_label.pack(fill=tk.X, padx=5, pady=2)

        self.progress_bar = ttk.Progressbar(scan_toolbar, orient=tk.HORIZONTAL, mode='determinate')

        # Image Canvas Container (using pack_propagate to avoid sizing loops)
        self.image_container = tk.Frame(mid_frame, bg="#EAEAEA")
        self.image_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.image_container.pack_propagate(False)

        self.canvas_label = tk.Label(self.image_container, bg="#EAEAEA", text="[ No Images Scanned ]\n\nClick 'Scan Directory for Faces' to begin.", font=("Arial", 10))
        self.canvas_label.pack(fill=tk.BOTH, expand=True)
        self.image_container.bind("<Configure>", self.on_container_resize)

        # Image status text
        self.image_status_label = tk.Label(mid_frame, text="", font=("Arial", 9, "bold"), fg="#333333")
        self.image_status_label.pack(pady=2)

        # Gallery Navigation
        nav_frame = tk.Frame(mid_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        self.btn_prev = tk.Button(nav_frame, text="◀ Previous", command=self.prev_image, width=12, font=("Arial", 9, "bold"))
        self.btn_prev.pack(side=tk.LEFT, padx=30)
        
        self.btn_next = tk.Button(nav_frame, text="Next ▶", command=self.next_image, width=12, font=("Arial", 9, "bold"))
        self.btn_next.pack(side=tk.RIGHT, padx=30)

        # PyWhatKit Automation Sending Action
        tk.Button(mid_frame, text="⚡ Send via PyWhatKit", bg="#075E54", fg="white", font=("Arial", 10, "bold"),
                  command=self.trigger_whatsapp_photo_send).pack(fill=tk.X, padx=10, pady=10)

        # -------------------------------------------------------------
        # RIGHT PANEL: Conversational Bot System
        # -------------------------------------------------------------
        right_frame = tk.LabelFrame(self.main_pane, text="Contextual WhatsApp Chatbot", width=350)
        self.main_pane.add(right_frame)

        self.chat_display = tk.Text(right_frame, state=tk.DISABLED, bg="#F7F9FA", wrap=tk.WORD, font=("Arial", 9))
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        input_frame = tk.Frame(right_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.user_msg_entry = tk.Entry(input_frame, font=("Arial", 10))
        self.user_msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.user_msg_entry.bind("<Return>", lambda event: self.process_chatbot_message())

        tk.Button(input_frame, text="Send", command=self.process_chatbot_message, bg="#007BFF", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=2)

    # -----------------------------------------------------------------
    # CONTROL LOGIC: Directory Scanning & Face Clustering (Async)
    # -----------------------------------------------------------------
    def start_directory_scan(self):
        directory = filedialog.askdirectory(title="Select Image Directory to Scan")
        if not directory:
            return
            
        self.btn_scan.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=2)
        self.progress_bar.config(value=0)
        self.status_label.config(text="Scanning directory...")
        
        scan_thread = threading.Thread(target=self.async_scan_and_cluster, args=(directory,))
        scan_thread.daemon = True
        scan_thread.start()

    def async_scan_and_cluster(self, directory):
        try:
            supported_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
            image_paths = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(supported_extensions):
                        image_paths.append(os.path.join(root, file))
            
            total_images = len(image_paths)
            if total_images == 0:
                self.root.after(0, lambda: self.finish_scan(False, "No images found in the selected directory."))
                return
                
            all_face_records = []  # list of tuples (image_path, encoding)
            
            for idx, path in enumerate(image_paths):
                progress_percent = int(((idx + 1) / total_images) * 100)
                status_text = f"Analyzing image {idx + 1}/{total_images}...\n{os.path.basename(path)}"
                self.root.after(0, lambda t=status_text, p=progress_percent: self.update_scan_progress(t, p))
                
                try:
                    # Load image using face_recognition
                    image = face_recognition.load_image_file(path)
                    # Detect face encodings
                    encodings = face_recognition.face_encodings(image)
                    for enc in encodings:
                        all_face_records.append((path, enc))
                except Exception as img_err:
                    print(f"Skipping file {path} due to error: {img_err}")
            
            if not all_face_records:
                self.root.after(0, lambda: self.finish_scan(False, "No faces detected in the scanned images."))
                return
            
            self.root.after(0, lambda: self.status_label.config(text="Clustering face encodings..."))
            
            # Extract encodings
            encodings = [rec[1] for rec in all_face_records]
            X = np.array(encodings)
            
            # DBSCAN Clustering (eps=0.55 is standard for L2 Euclidean face encoding distance)
            db = DBSCAN(eps=0.55, min_samples=1, metric="euclidean")
            labels = db.fit_predict(X)
            
            # Map face clustering labels to image paths
            # If multiple faces exist in a group photo, they might cluster to different labels.
            # Thus, a single group photo will map to multiple label lists.
            cluster_images = {}
            noise_counter = 0
            
            for i, label in enumerate(labels):
                path = all_face_records[i][0]
                if label == -1:
                    label_key = f"noise_{noise_counter}"
                    noise_counter += 1
                else:
                    label_key = int(label)
                    
                if label_key not in cluster_images:
                    cluster_images[label_key] = set()
                cluster_images[label_key].add(path)
            
            # Sort clusters by number of images (largest first)
            sorted_clusters = sorted(cluster_images.items(), key=lambda item: len(item[1]), reverse=True)
            
            new_labels_data = {}
            for index, (lbl, paths) in enumerate(sorted_clusters):
                person_name = f"Person_{index + 1}"
                new_labels_data[person_name] = sorted(list(paths))
            
            self.root.after(0, lambda: self.finish_scan(True, new_labels_data))
            
        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda: self.finish_scan(False, f"An error occurred: {str(e)}"))

    def update_scan_progress(self, text, percent):
        self.status_label.config(text=text)
        self.progress_bar.config(value=percent)

    def finish_scan(self, success, result):
        self.progress_bar.pack_forget()
        self.btn_scan.config(state=tk.NORMAL)
        
        if success:
            self.labels_data = result
            self.refresh_labels_listbox()
            self.status_label.config(text=f"Scan complete! Clustered into {len(result)} People.")
            # Select first label automatically
            if self.labels_box.size() > 0:
                self.labels_box.selection_set(0)
                self.on_label_select(None)
            messagebox.showinfo("Scan Success", f"Face clustering complete! Identified {len(result)} individuals.")
        else:
            self.status_label.config(text="Scan failed.")
            messagebox.showerror("Scan Error", result)

    # -----------------------------------------------------------------
    # CONTROL LOGIC: Label Management (CRUD)
    # -----------------------------------------------------------------
    def refresh_labels_listbox(self):
        self.labels_box.delete(0, tk.END)
        for label in self.labels_data.keys():
            self.labels_box.insert(tk.END, label)

    def on_label_select(self, event):
        selected_index = self.labels_box.curselection()
        if not selected_index:
            return
            
        selected_label = self.labels_box.get(selected_index[0])
        self.image_list = self.labels_data.get(selected_label, [])
        self.current_img_index = 0
        self.update_image_preview()

    def add_label(self):
        new_label = simpledialog.askstring("New Person Label", "Enter your new person name:")
        if new_label and new_label.strip():
            new_label_clean = new_label.strip()
            if new_label_clean not in self.labels_data:
                self.labels_data[new_label_clean] = []
                self.refresh_labels_listbox()
                
                # Select the newly created label
                for idx, label in enumerate(self.labels_data.keys()):
                    if label == new_label_clean:
                        self.labels_box.selection_set(idx)
                        break
                self.on_label_select(None)
            else:
                messagebox.showwarning("Warning", "Label name already exists.")

    def rename_label(self):
        selected_index = self.labels_box.curselection()
        if not selected_index:
            messagebox.showwarning("Selection Missing", "Please select a label from the sidebar first.")
            return
        
        old_name = self.labels_box.get(selected_index)
        new_name = simpledialog.askstring("Rename Label", f"Modify identity for '{old_name}':", initialvalue=old_name)
        
        if new_name and new_name.strip() and new_name != old_name:
            new_name_clean = new_name.strip()
            self.labels_data[new_name_clean] = self.labels_data.pop(old_name)
            self.refresh_labels_listbox()
            
            # Select the newly renamed label
            for idx, label in enumerate(self.labels_data.keys()):
                if label == new_name_clean:
                    self.labels_box.selection_set(idx)
                    break
            self.on_label_select(None)

    def delete_label(self):
        selected_index = self.labels_box.curselection()
        if not selected_index:
            messagebox.showwarning("Selection Missing", "Please select a label to delete.")
            return
        
        target = self.labels_box.get(selected_index)
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete label '{target}'?"):
            del self.labels_data[target]
            self.refresh_labels_listbox()
            self.image_list = []
            self.current_img_index = 0
            self.update_image_preview()

    def add_photo_to_label(self):
        selected_index = self.labels_box.curselection()
        if not selected_index:
            messagebox.showwarning("Selection Missing", "Please select a Person/Label from the sidebar first.")
            return
            
        selected_person = self.labels_box.get(selected_index[0])
        
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp")]
        )
        
        if file_path:
            file_path = os.path.normpath(file_path)
            if selected_person not in self.labels_data:
                self.labels_data[selected_person] = []
            
            # Avoid duplicates
            if file_path not in self.labels_data[selected_person]:
                self.labels_data[selected_person].append(file_path)
                self.labels_data[selected_person].sort()
                
            # Refresh gallery view
            self.image_list = self.labels_data[selected_person]
            self.current_img_index = self.image_list.index(file_path)
            self.update_image_preview()
            messagebox.showinfo("Success", f"Added image to '{selected_person}' successfully.")

    # -----------------------------------------------------------------
    # CONTROL LOGIC: Gallery Nav & Keyboard Events
    # -----------------------------------------------------------------
    def bind_keyboard_events(self):
        self.root.bind("<Left>", lambda event: self.prev_image())
        self.root.bind("<Right>", lambda event: self.next_image())

    def next_image(self):
        if self.image_list:
            self.current_img_index = (self.current_img_index + 1) % len(self.image_list)
            self.update_image_preview()

    def prev_image(self):
        if self.image_list:
            self.current_img_index = (self.current_img_index - 1) % len(self.image_list)
            self.update_image_preview()

    def on_container_resize(self, event):
        self.update_image_preview()

    def update_image_preview(self):
        if not self.image_list:
            self.canvas_label.config(
                image='', 
                text="[ No Images Associated ]\n\nClick 'Scan Directory for Faces' to automatically cluster\nor click 'Add Photo to Selected Label' to link photos manually.",
                font=("Arial", 10)
            )
            self.image_status_label.config(text="")
            return
            
        if self.current_img_index >= len(self.image_list):
            self.current_img_index = 0
        elif self.current_img_index < 0:
            self.current_img_index = len(self.image_list) - 1
            
        current_img = self.image_list[self.current_img_index]
        
        if not os.path.exists(current_img):
            self.canvas_label.config(image='', text=f"File not found:\n{current_img}", font=("Arial", 10))
            self.image_status_label.config(text="")
            return
            
        try:
            pil_img = Image.open(current_img)
            
            # Obtain actual container dimensions for dynamic resize
            w = self.image_container.winfo_width()
            h = self.image_container.winfo_height()
            
            if w <= 10 or h <= 10:
                w = 450
                h = 350
                
            img_w, img_h = pil_img.size
            ratio = min(w / img_w, h / img_h)
            new_w = max(1, int(img_w * ratio))
            new_h = max(1, int(img_h * ratio))
            
            resized_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized_img)
            
            self.canvas_label.config(image=self.tk_image, text="")
            self.image_status_label.config(text=f"Image {self.current_img_index + 1} of {len(self.image_list)}: {os.path.basename(current_img)}")
        except Exception as e:
            self.canvas_label.config(image='', text=f"Error loading image:\n{e}", font=("Arial", 10))
            self.image_status_label.config(text="")

    # -----------------------------------------------------------------
    # CONTROL LOGIC: Chatbot Framework With Auto-Purge History
    # -----------------------------------------------------------------
    def log_to_chat_window(self, sender, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def process_chatbot_message(self):
        user_text = self.user_msg_entry.get().strip()
        if not user_text:
            return
        
        self.user_msg_entry.delete(0, tk.END)
        self.log_to_chat_window("You", user_text)
        
        # Append message to persistent session tracking arrays
        self.chat_history.append({"role": "user", "text": user_text})

        # Process standard rules or hand-off to dynamic automated routing
        response_text = ""
        completion_triggered = False

        # Context-Aware Rules Logic Example
        lowered_text = user_text.lower()
        if "hello" in lowered_text or "hi" in lowered_text:
            response_text = "Hello! I am your automated virtual worker framework. How can I help with your project queues today?"
        elif "status" in lowered_text:
            total_images = sum(len(paths) for paths in self.labels_data.values())
            response_text = f"We have {len(self.labels_data)} people labels active and {total_images} total linked images across them."
        elif "done" in lowered_text or "complete" in lowered_text or "exit" in lowered_text:
            response_text = "Understood. Ending conversation parameters and completely wiping volatile short-term session storage histories now..."
            completion_triggered = True
        else:
            # Memory Context Tracking Demo:
            response_text = f"I am keeping track of our session context. Your past query was logged. (Type 'complete' to wipe context records)."

        self.log_to_chat_window("Bot", response_text)
        self.chat_history.append({"role": "bot", "text": response_text})

        if completion_triggered:
            # Enforce strict post-completion session wipe
            self.root.after(2500, self.clear_chat_session)

    def clear_chat_session(self):
        self.chat_history.clear()
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete('1.0', tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.log_to_chat_window("System", "🧹 Session database cache auto-purged successfully.")

    # -----------------------------------------------------------------
    # CONTROL LOGIC: Thread-Safe Background PyWhatKit Executions
    # -----------------------------------------------------------------
    def trigger_whatsapp_photo_send(self):
        if not self.image_list:
            messagebox.showwarning("No Image", "There is no active image to send.")
            return
            
        target_number = simpledialog.askstring("Send WhatsApp", "Enter recipient mobile number (with country code, e.g., +919876543210):")
        if not target_number or not target_number.strip():
            return
            
        target_number = target_number.strip()
        
        # Prevent threading lockups inside the primary GUI viewport thread loop
        worker_thread = threading.Thread(target=self.async_pywhatkit_worker, args=(target_number,))
        worker_thread.daemon = True
        worker_thread.start()

    def async_pywhatkit_worker(self, target_number):
        active_image = self.image_list[self.current_img_index]
        
        # Verify document nodes on host storage paths to prevent fatal runtime OS errors
        if not os.path.exists(active_image):
            messagebox.showerror("IO Fault", f"The resource reference target location could not be located:\n{os.path.abspath(active_image)}")
            return

        try:
            # Run background driver calling window coordinates hooks
            kit.sendwhats_image(receiver=target_number, img_path=active_image, caption="Automated Image Shared via Drishyamitra")
        except Exception as err:
            messagebox.showerror("Automation Routine Breakpoint Error", str(err))

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedWhatsAppBotApp(root)
    root.mainloop()
