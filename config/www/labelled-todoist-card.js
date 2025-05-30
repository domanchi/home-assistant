//  General Notes:
//    - This is loaded inline with the dashboard. So you can use console.log for debugging.
//
//  Organization:
//    TodistCardList:              main component
//     |- Header:                  title and action buttons
//     |- TodoistQuickAdd:         quick add input field
//     |- TodoistLabelledSection:  each individual expandable, draggable label
//     |
//    DialogTodoistItemEditor:     component to edit entries


//  LitElement is used for drop-in support for improved HTMLElement capabilities.
import {LitElement, html, css} from "https://cdn.jsdelivr.net/npm/lit@3.3.0/+esm";
import {keyed} from "https://unpkg.com/lit@3.3.0/directives/keyed.js?module";

//
//  Install dependencies.
//

function loadCSS(url) {
  const link = document.createElement("link");
  link.type = "text/css";
  link.rel = "stylesheet";
  link.href = url;
  
  //  NOTE: Need to inject this class value to the html tag for the CSS rule to kick in.
  link.onload = () => {
    document.documentElement.classList.add("sl-theme-dark");
  }

  document.head.appendChild(link);
}

//  Add shoelace CSS to window.
//  For more details, see https://shoelace.style/.
loadCSS("https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/themes/dark.css");

function loadModuleDependency(url) {
  const script = document.createElement("script");
  script.type = "module";
  script.src = url;

  document.head.appendChild(script);
}

//  NOTE: This author couldn't get setBasePath working, and it turns out that the "intelligence"
//  of shoelace's imported libraries cares about whether you use the `import` directive
//  (i.e. ES6 javascript style), or adding it to the document head.
//
//  Therefore, we have to inject the entire bundle at document head (because the author couldn't
//  figure out cherry picking too).
loadModuleDependency("https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/shoelace.js");

//
//  Customized components.
//

const DOMAIN = "todoist";

/**
* TodistCardList renders todo lists grouped by labels.
*/
class TodoistCardList extends LitElement {
  static get properties() {
    return {
      //  Access to the parent HomeAssistant module.
      hass: Object,
      
      //  Configuration for this widget specifically.
      config: Object,
    }
  }

  constructor() {
    super();

    this.localChanges = [];
  }

  render() {
    //
    //  Input validation.
    //  TODO: Better sample data?
    //

    if (!this.hass || !this.config.entity) {
      return this.displayError("unconfigured parameters");
    }

    //  TODO: check for saver.saver.
    if (!this.hass.states[this.config.entity].attributes.items.length) {
      return this.displayError("invalid entity: must have todoist API data");
    }

    //
    //  Organize by labels.
    //

    const labelsMapping = this.getLabelsMapping(this.hass.states[this.config.entity].attributes.items);
    if (Object.entries(labelsMapping).length === 0) {
      return this.displayError("no results to display");
    }

    const alphabetical = Object.keys(labelsMapping).sort();
    let ordering = alphabetical;
    
    const state = this.getState();
    const sortMode = state.sortMode || "default";
    if (sortMode === "default" && state.order && state.order.length > 0) {
      ordering = state.order;
    } else if (sortMode === "descending") {
      ordering = alphabetical.slice().reverse();
    }

    //  Handle the case in which items are filtered out.
    //  If we have a saved order (with hidden items), filter the current ordering to only
    //  show visible items.
    if (state.order && ordering !== state.order) {
      ordering = ordering.filter(label => state.order.includes(label));
    }

    const sections = this.applyLocalChanges(ordering);

    return html`
      <ha-card>
        <todoist-header>
          ${this.hass.states[this.config.entity].attributes.name}
          
          <div slot="actions">
            ${ordering.length < alphabetical.length ? html`
              <ha-icon-button 
                title="Show hidden labels (${alphabetical.length - ordering.length} hidden)"
                @click=${this.showAllHiddenSections}
              >
                <ha-icon icon="mdi:eye"></ha-icon>
              </ha-icon-button>
            ` : ''}
            
            <ha-icon-button 
              title="Sort"
              @click=${this.handleSort}>
              <ha-icon icon="${this.getSortIcon(sortMode)}"></ha-icon>
            </ha-icon-button>
          </div>
        </todoist-header>
        
        <todoist-quick-add
          .hass=${this.hass}
          .project=${this.hass.states[this.config.entity].attributes.name}
          .onAdd=${(item) => this.handleItemAdd(item)}
        ></todoist-quick-add>

        ${Object.entries(sections).map(
          //  NOTE: These callbacks need to be routed to this layer because
          //  this layer manages state. State could be pushed down, but I don't know
          //  how well HomeAssistant's pub/sub handles _multiple_ read/writes per render.
          ([key, value]) => html`
            <todoist-labelled-section
              draggable="true"
              data-label="${key}"

              .title=${key}
              .items=${value}
              .open=${state.isOpen ? state.isOpen.includes(key) : false}

              .onToggle=${(e, labelKey) => this.handleToggle(e, labelKey)}
              .onDelete=${(e, labelKey) => this.handleDeleteSection(e, labelKey)}
              .onItemToggle=${(e, item) => this.handleItemToggle(e, item)}
              .onItemClick=${(e, item) => this.handleItemClick(e, item)}

              @dragstart=${(e) => this.handleDragStart(e)}
              @dragover=${(e) => this.handleDragOver(e)}
              @drop=${(e) => this.handleDrop(e)}
              @dragend=${(e) => this.handleDragEnd(e)}
            >
            </todoist-labelled-section>
          `
        )}

      </ha-card>
    `;
  }
  
  //
  //  Persistent state management
  //

  /**
   * @returns object
   *   {
   *     sortMode: "",  // "default", "ascending" or "descending"
   *     order: [],     // list of labels to display (in order)
   *     isOpen: [],    // list of labels that are open
   *   }
   */
  getState() {
    const key = `${DOMAIN}.${this.config.entity}`;
    const state = this.hass.states["saver.saver"].attributes.variables[key];
    if (!state) {
      return {};
    }

    return JSON.parse(state);
  }

  saveState(state) {
    const key = `${DOMAIN}.${this.config.entity}`;
    this.hass.callService(
      "saver",
      "set_variable",
      {
        name: key,
        value: JSON.stringify(state),
      },
    );
  }

  //
  //  Handle local state management
  //

  /**
   * This smoothens the network requests between client and server by emulating server changes
   * in client code, until server changes have aligned. Note that state does not need to be
   * persisted (i.e. via `saver.saver`) because that's what the server is for.
   *
   * @param {array} currentOrder list of labels to display
   * @returns {object} adjusted list of sections to display.
   *    - deleted items will be moved to the bottom of the list (still visible until
   *      server removes it)
   *    - added items will be added to the bottom of the list
   *    - after server confirms changes, the local state will be amended.
   */
  applyLocalChanges(currentOrder) {
    const allServerItems = this.hass.states[this.config.entity].attributes.items;
    const serverLabels = this.getLabelsMapping(allServerItems);

    // Create a set of content from server items for efficient lookup
    const serverItemsContentSet = new Set(allServerItems.map(item => item.content));

    // Pre-filter this.localChanges:
    // 1. Remove 'add' type items if their content is already present on the server.
    // 2. Remove 'delete' type items if their content is NO LONGER present on the server
    //    (meaning server has processed deletion).
    //
    // NOTE: Assumes content is unique.
    this.localChanges = this.localChanges.filter(localItem => {
        if (localItem.type === "add") {
            // Keep 'add' item only if its content is NOT on the server
            return !serverItemsContentSet.has(localItem.content);
        }
        if (localItem.type === "delete") {
            // Keep 'delete' item only if its content IS STILL on the server
            // (deletion not yet processed by server)
            return serverItemsContentSet.has(localItem.content);
        }

        //  TODO: handle type === update, from the update workflow.
        //  Without this, there will be a 30s delay between making changes, and seeing them.
        return true;
    });

    // Use the cleaned this.localChanges to get localLabels
    const localLabels = this.getLabelsMapping(this.localChanges);

    const output = {};
    for (const label of currentOrder) {
      // If no local changes for this label (after cleaning), use server data.
      if (!localLabels.hasOwnProperty(label)) {
        output[label] = serverLabels[label] || [];
        continue;
      }

      // Get local 'add' and 'delete' items for the current label from the cleaned localChanges.
      const addedItemsForLabel = (localLabels[label] || []).filter(item => item.type === "add");
      const serverItemsForLabel = serverLabels[label] || [];

      const deletedItemsForLabel = (localLabels[label] || []).filter(item => item.type === "delete");
      for (const item of deletedItemsForLabel) {
        item.scheduledForDeletion = true;
      }

      // Construct the list of items for the current label:
      // 1. Start with server items for this label.
      // 2. Filter out any server items that are marked for deletion in localChanges for this label.
      // 3. Append locally added items for this label (these are now confirmed not to be on the server).
      // 4. Append locally deleted items for this label (to show them at the end, as per original logic).
      //
      // NOTE: Assumes content is unique.
      const reorderedItems = [
        ...serverItemsForLabel.filter(
          serverItem => !deletedItemsForLabel.some(deletedItem => deletedItem.content === serverItem.content)
        ),
        ...addedItemsForLabel,
        ...deletedItemsForLabel 
      ];
      output[label] = reorderedItems;
    }

    return output;
  }

  handleItemAdd(item) {
    this.localChanges.push({...item, type: "add"});
    this.requestUpdate();
  }

  //
  //  Handle toggle state
  //

  handleToggle(e, labelKey) {
    const state = this.getState();
    let isOpen = state.isOpen || [];
    
    if (e.target.open) {
      // Add to open list if not already there
      if (!isOpen.includes(labelKey)) {
        isOpen.push(labelKey);
      }
    } else {
      // Remove from open list
      isOpen = isOpen.filter(key => key !== labelKey);
    }
    
    this.saveState({ ...state, isOpen: isOpen });
  }

  /**
   * This function is used to mark items off the list.
   *
   * @param {Event} e
   * @param {object} item
   */
  handleItemToggle(e, item) {
    e.stopPropagation();

    if (e.target.selected) {
      // Item is checked, mark for deletion
      this.localChanges.push({...item, type: "delete"});

      this.hass.callService(
        "rest_command",
        "todoist_close_task",
        {
          task_id: item.id,
        },
      );
    } else {
      // Item is unchecked, remove from deletion if it was marked
      this.localChanges = this.localChanges.filter(change => 
        !(change.id === item.id && change.type === "delete")
      );

      this.hass.callService(
        "rest_command",
        "todoist_reopen_task",
        {
          task_id: item.id,
        },
      );
    }

    //  Fix strange case where focus is persisted.
    document.activeElement.blur();

    // Ensure UI updates after localChanges modification
    this.requestUpdate();
  }

  handleItemClick(e, item) {
    let dialog = document.querySelector("dialog-todoist-item-editor");
    if (!dialog) {
      dialog = document.createElement('dialog-todoist-item-editor');
    
        // Remove active focus to deconflict between the dialog's autofocus.
      document.activeElement.blur();
      
      // Append the dialog to the body
      document.body.appendChild(dialog);
    } else {
      //  Show dialog (instead of creating a new one).
      dialog.shadowRoot.querySelector("sl-dialog").show()
    }

    dialog.hass = this.hass;
    dialog.item = item;
  }

  //
  //  Handle sorting
  //

  handleSort() {
    const state = this.getState();
    let currentMode = state.sortMode || "default";
    
    // Cycle through sort modes: default -> ascending -> descending -> default
    let newMode;
    if (currentMode === "default") {
      newMode = "ascending";
    } else if (currentMode === "ascending") {
      newMode = "descending";
    } else {
      newMode = "default";
    }
    
    // Save the new sort mode
    this.saveState({ ...state, sortMode: newMode });
  }

  getSortIcon(sortMode) {
    if (sortMode === "ascending") {
      return "mdi:sort-alphabetical-ascending";
    } else if (sortMode === "descending") {
      return "mdi:sort-alphabetical-descending";
    }
    return "mdi:sort";
  }

  //
  //  Handle sortable sections
  //

  showAllHiddenSections() {
    const state = this.getState();
    const allLabels = Object.keys(
      this.getLabelsMapping(this.hass.states[this.config.entity].attributes.items)
    ).sort();
    const currentOrder = state.order || allLabels;
    
    // Find hidden labels (labels that exist in data but not in current order)
    const hiddenLabels = allLabels.filter(label => !currentOrder.includes(label));
    
    // Add hidden labels to the end of the current order
    const newOrder = [...currentOrder, ...hiddenLabels];
    
    // Save the updated state
    this.saveState({ ...state, order: newOrder });
  }

  handleDeleteSection(e, labelKey) {
    e.stopPropagation(); // Prevent triggering the sl-details toggle
    e.preventDefault();  // Prevent other default behavior

    const state = this.getState();
    let ordering = state.order || Object.keys(
      this.getLabelsMapping(this.hass.states[this.config.entity].attributes.items)
    ).sort();
    
    // Remove the section from the ordering
    ordering = ordering.filter(key => key !== labelKey);
    
    // Also remove from isOpen if it was open
    let isOpen = state.isOpen || [];
    isOpen = isOpen.filter(key => key !== labelKey);
    
    // Save the updated state
    this.saveState({ ...state, order: ordering, isOpen: isOpen });
  }

  reorderSections(draggedLabel, targetLabel) {
    const state = this.getState();
    let ordering = state.order || Object.keys(this.getLabelsMapping(
      this.hass.states[this.config.entity].attributes.items
    )).sort();
    
    // Remove dragged item and insert at new position
    const draggedIndex = ordering.indexOf(draggedLabel);
    const targetIndex = ordering.indexOf(targetLabel);
    
    ordering.splice(draggedIndex, 1);
    ordering.splice(targetIndex, 0, draggedLabel);
    
    // Save new order
    this.saveState({ ...state, order: ordering });
  }

  //
  //  Handle drag and drop
  //

  handleDragStart(e) {
    //  NOTE: We need to save a reference to the dragged item, because we can't do it anywhere
    //  else, and the event for [handleDragOver] uses a different target.
    this.dragged = e.currentTarget.dataset.label;
    
    e.target.classList.add("dragging");
  }

  handleDragOver(e) {
    e.preventDefault();
    
    // Remove existing drop indicators
    this.clearDropIndicators();
    
    // Add drop indicator to current target.
    // NOTE: Since this is a "dragover" event, the target is the target being "dragged over".
    const targetLabel = e.currentTarget.dataset.label;

    // Don't show drop indicator on the dragged element itself or if it's the same element
    if (this.dragged === targetLabel) {
      return
    }

    // NOTE: Handle cases in which this is missing.
    if (!e.target.classList) {
      return
    }

    // Determine if we're moving up or down
    const state = this.getState();
    const currentOrder = state.order || Object.keys(this.getLabelsMapping(
      this.hass.states[this.config.entity].attributes.items
    )).sort();
    const draggedIndex = currentOrder.indexOf(this.dragged);
    const targetIndex = currentOrder.indexOf(targetLabel);
    
    if (draggedIndex > targetIndex) {
      // Moving up - show line above target
      e.target.classList.add("drop-target-above");
    } else {
      // Moving down - show line below target
      e.target.classList.add("drop-target-below");
    }
  }

  handleDrop(e) {
    e.preventDefault();
    this.clearDropIndicators();
    
    const targetLabel = e.currentTarget.dataset.label;
    if (this.dragged !== targetLabel) {
      this.reorderSections(this.dragged, targetLabel);
    }
  }

  handleDragEnd(e) {
    e.target.classList.remove("dragging");
    this.clearDropIndicators();
  }

  clearDropIndicators() {
    const sections = this.shadowRoot.querySelectorAll('todoist-labelled-section');
    sections.forEach(section => {
      section.classList.remove('drop-target-above', 'drop-target-below');
    });
  }

  /**
   * @returns a mapping of label => [items...]
   */
  getLabelsMapping(items) {
    const labelsMapping = {};
    for (const i of items) {
      for (const label of i.labels) {
        labelsMapping[label] = labelsMapping[label] || [];
        labelsMapping[label].push(i);
      }
    }
    
    return labelsMapping;
  }

  displayError(message) {
    return html`<div>error: ${message}</div>`;
  }

  static styles = css`
    ha-card {
      height: 100%;
      box-sizing: border-box;
      overflow-y: auto;
    }

    todoist-labelled-section {
      position: relative;
    }

    todoist-labelled-section.dragging {
      opacity: 0.5;
      cursor: grabbing;
    }

    todoist-labelled-section.drop-target-above::before {
      content: "";
      position: absolute;
      top: -2px;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--primary-color, #03a9f4);
      border-radius: 2px;
      box-shadow: 0 0 8px rgba(3, 169, 244, 0.6);
      z-index: 1000;
    }

    todoist-labelled-section.drop-target-below::after {
      content: "";
      position: absolute;
      bottom: -2px;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--primary-color, #03a9f4);
      border-radius: 2px;
      box-shadow: 0 0 8px rgba(3, 169, 244, 0.6);
      z-index: 1000;
    }
  `;
  
  //
  //  Upstream integrations
  //  https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
  //
  
  //  Use the built-in form-builder to make defining configuration easier.
  //  For more information, see https://github.com/home-assistant/frontend/blob/dev/src/components/ha-form/types.ts
  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: {
            entity: {
              domain: "sensor",
            },
          },
        },
      ],
      
      //  Input validation.
      //
      //  NOTE: Any errors thrown will cause the visual editor to hard fail.
      //  NOTE: We don't get access to the hass object here (because static function).
      assertConfig: (config) => {
        //  TODO: Is this needed?
      },
      
      //  Don't need one, because not doing internationalization.
      computeLabel: null,
    };
  }
  
  setConfig(config) {
    this.config = config;
  }
}

/**
 * Header encapsulates related styles and API calls for colocated
 * action buttons.
 */
class Header extends LitElement {
  static get properties() {
    return {}
  }

  render() {
    return html`
      <div class="header-wrapper">
        <div class="header-top">
          <h2 class="title">
            <ha-icon icon="mdi:format-list-checks" class="title-icon"></ha-icon>
            <slot></slot>
          </h2>
          <div class="actions">
            <slot name="actions"></slot>
          </div>
        </div>
        <div class="description">
          <p class="description-text">
            Add new tasks below. Use labels like <code>@costco</code>, <code>@trader-joes</code> 
            to organize items into sections, and set priorities with <code>p1</code>.

            <a href="https://www.todoist.com/help/articles/use-task-quick-add-in-todoist-va4Lhpzz" 
                target="_blank" 
                class="help-link">
              <ha-icon icon="mdi:help-circle-outline"></ha-icon>
            </a>
          </p>
        </div>
      </div>
    `;
  }

  handleSortClick() {
    if (this.onSort) {
      this.onSort();
    }
  }

  static styles = css`
    :host {
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    .header-wrapper {
      display: flex;
      flex-direction: column;
      
      padding-left: 16px;
      padding-right: 16px;
      padding-top: 10px;
    }

    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .title {
      margin: 0;
      font-size: 1.4em;
      font-weight: 600;
      color: var(--primary-text-color);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .title-icon {
      color: var(--primary-color, #03a9f4);
      --mdc-icon-size: 24px;
    }

    .actions {
      display: flex;
      gap: 4px;
      align-items: center;
    }

    .actions ha-icon-button {
      --mdc-icon-button-size: 40px;
      --mdc-icon-size: 20px;
      color: var(--secondary-text-color);
      transition: color 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .actions .ha-icon-button ha-icon {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .actions ha-icon-button:hover {
      color: var(--primary-color, #03a9f4);
      background-color: var(--primary-color-alpha, rgba(3, 169, 244, 0.1));
    }

    .description {
      margin: 0;
    }

    .description-text {
      margin: 2px 0 8px 0;
      font-size: 0.9em;
      color: var(--secondary-text-color);
      line-height: 1.5;
    }

    code {
      background-color: var(--code-background, rgba(255, 255, 255, 0.1));
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.85em;
      color: var(--primary-color, #03a9f4);
    }

    .help-link {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      color: var(--secondary-text-color);
      text-decoration: none;
      font-size: 0.85em;
      transition: color 0.2s ease;
    }

    .help-link:hover {
      color: var(--primary-color, #03a9f4);
      text-decoration: underline;
    }

    .help-link ha-icon {
      --mdc-icon-size: 16px;
    }
  `;
}

class TodoistQuickAdd extends LitElement {
  static get properties() {
    return {
      hass: Object,
      project: {
        type: String,
      },

      //  This will be triggered on a successful item addition.
      onAdd: {
        type: Function,
      },
    }
  }

  render() {
    return html`
      <div class="container">
        <ha-textfield 
          placeholder="Add Item" 
          @keydown=${this.handleKeyDown}
        ></ha-textfield>
        <ha-icon-button 
          title="Add Item" 
          @click=${this.handleAddItem}
        >
          <ha-icon icon="mdi:plus"></ha-icon>
        </ha-icon-button>
      </div>
    `;
  }

  handleKeyDown(e) {
    if (e.key === 'Enter') {
      this.handleAddItem();
    }
  }

  /**
   * Processes the text field, and returns the parsed content (subset of Todoist's syntax).
   * @returns object
   *    {
   *        "labels": [],
   *        "content": "",
   *        "raw": "",
   *    }
   */
  parseContent() {
    const textfield = this.shadowRoot.querySelector('ha-textfield');
    const value = textfield.value.trim();
    if (!value) {
      return null;
    }

    const labels = [];
    let content = value;

    // Regex to find @labels
    const labelRegex = /@([\w-]+)/g;
    let match;
    while ((match = labelRegex.exec(content)) !== null) {
      labels.push(match[1]);
    }

    // Remove labels from content string
    content = content.replace(labelRegex, '').trim();
    
    // Remove extra spaces that might be left after removing labels
    content = content.replace(/\s\s+/g, ' ').trim();

    return {
      labels: labels,
      content: content,
      raw: value,
    };
  }

  handleAddItem() {
    const content = this.parseContent();
    if (!content) {
      return
    }

    // Clear the textfield after adding
    this.shadowRoot.querySelector('ha-textfield').value = '';

    this.hass.callService(
      "rest_command",
      "todoist_quick_add",
      {
        //  NOTE: Add the project to the payload by default, because we
        //  assume that the component only tracks within a single project.
        text: `#${this.project} ${content.raw}`,
      },
    );

    if (this.onAdd) {
      this.onAdd(content);
    }
  }

  static styles = css`
    .container {
      display: flex;
      flex-direction: row;
      align-items: center;

      padding-bottom: 0.6vh;
      padding-top: 0;
      padding-left: 16px;
      padding-right: 16px;
      position: relative;
    }

    ha-textfield {
      flex-grow: 1;
    }

    ha-icon-button {
      position: absolute;
      right: 16px;
      inset-inline-start: initial;
      inset-inline-end: 16px;
    }
  `;
}

class TodoistLabelledSection extends LitElement {
  static get properties() {
    return {
      title: {
        type: String,
      },
      items: {
        type: Array,
      },

      //  If true, this will expand the sl-details component.
      open: {
        type: Boolean,
      },

      //  Callback to trigger when the sl-details component is opened/closed.
      onToggle: {
        type: Function,
      },

      //  Callbaack to trigger when the sl-details component has been hidden.
      onDelete: {
        type: Function,
      },

      //  Callback to trigger when one of the list items' checkboxes is selected.
      onItemToggle: {
        type: Function,
      },

      //  Callback to trigger when one of the list items is selected.
      onItemClick: {
        type: Function,
      },
    }
  }

  constructor() {
    super();
    this.items = [];
    this.open = false;
  }

  render() {
    if (!this.items || !this.items.length) {
      return html``;
    }

    // Format the display title
    const displayTitle = this.title
      .split("-")
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ") + ` (${this.items.length})`;

    const listItems = this.items.map(item => 
      keyed(item.id || item.content, html`
        <ha-check-list-item
          left
          .selected=${item.scheduledForDeletion || false}
          @change=${(e) => this.handleItemToggle(e, item)}
          @click=${(e) => this.handleItemClick(e, item)}
        >
          <div class="column">
            <div class="headline">${item.content}</div>
            ${item.description ? html`
              <ha-markdown-element
                content=${item.description}
                allowSvg=${true}
                lazyImages=${true}
              >
              </ha-markdown-element>
            ` : ''}
          </div>
        </ha-check-list-item>
      `)
    );

    return html`
      <div>
        <sl-details 
          ?open=${this.open}
          @sl-show=${this.handleToggle}
          @sl-hide=${this.handleToggle}
        >
          <div slot="summary" class="summary-container">
            <span class="summary-text">${displayTitle}</span>
            <ha-icon 
              class="hide-icon"
              icon="mdi:eye-off"
              @click=${this.handleDelete}
            ></ha-icon>
          </div>
          <div class="checklist-container">
            ${listItems}
          </div>
        </sl-details>
      </div>
    `;
  }

  handleToggle(e) {
    if (this.onToggle) {
      this.onToggle(e, this.title);
    }
  }

  handleDelete(e) {
    e.stopPropagation();
    e.preventDefault();
    if (this.onDelete) {
      this.onDelete(e, this.title);
    }
  }

  handleItemToggle(e, item) {
    if (this.onItemToggle) {
      this.onItemToggle(e, item);
    }
  }

  handleItemClick(e, item) {
    if (!this.onItemClick) {
      return
    }

    if (!this.isValidClickEvent(e)) {
      return
    }

    this.onItemClick(e, item);
  }

  /**
   * Apparently, when we click on a list item, it sends _both_ the click event and the
   * change event. Since we don't want to trigger the change event when the change event
   * is rightfully toggled, we need to do some magic to determine the difference.
   *
   * @param {Event} e 
   * @returns bool
   */
  isValidClickEvent(e) {
    // e.composedPath() returns an array of the event's path, useful for Shadow DOM.
    const path = e.composedPath && e.composedPath();
    let clickedOnCheckbox = false;

    if (path) {
      clickedOnCheckbox = path.some(
        (el) => el.tagName === 'MWC-CHECKBOX' || el.tagName === 'HA-CHECKBOX'
      );
    } else if (e.target && (e.target.tagName === 'MWC-CHECKBOX' || e.target.tagName === 'HA-CHECKBOX')) {
      // Fallback for browsers not supporting composedPath or if path is null/empty
      // This checks if the direct target was a checkbox.
      clickedOnCheckbox = true;
    }

    return !clickedOnCheckbox;
  }

  static styles = css`
  /** Checklist items styling */
  .checklist-container {
    padding: 0;
    background-color: transparent;
  }

  ha-check-list-item {
    padding: 8px 16px;
    min-height: fit-content;
    height: auto;
    
    /* Remove borders */
    border: none;
    border-bottom: none;
    
    /* Responsive layout */
    display: flex;
    align-items: flex-start;
    gap: 12px;
    
    /* Let content determine size */
    --mdc-list-item-graphic-size: auto;
    --mdc-list-item-graphic-margin: 12px;
    --mdc-list-item-leading-width: auto;
    --mdc-list-item-leading-height: auto;
  }

  /* Simplified part overrides */
  ha-check-list-item::part(container) {
    padding: 0;
    height: auto;
    min-height: auto;
  }

  ha-check-list-item::part(start) {
    margin-inline-end: 12px;
    flex-shrink: 0;
    align-self: flex-start;
    margin-top: 2px;
  }

  ha-check-list-item::part(content) {
    flex: 1;
    min-width: 0; /* Allow text to wrap */
    width: 100%;
  }

  ha-check-list-item::part(end) {
    display: none;
  }

  /* Hover effects */
  ha-check-list-item:active {
    background-color: var(--primary-color-alpha, rgba(3, 169, 244, 0.1));
  }

  /* Styling for completed items */
  ha-check-list-item[selected] {
    opacity: 0.7;
    background-color: var(--success-color-alpha, rgba(76, 175, 80, 0.1));
  }

  /* Text content styling - content-responsive */
  ha-check-list-item .column {
    margin-top: 10px;
  }

  ha-check-list-item div.headline {
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    color: var(--primary-text-color);
    margin: 0;
    word-wrap: break-word;
    word-break: break-word;
    white-space: normal;
    overflow-wrap: break-word;
    hyphens: auto;
    width: 100%;
    display: block;
  }

  ha-check-list-item ha-markdown-element {
    font-size: 12px;
    line-height: 1.4;
    color: var(--secondary-text-color);
    margin-top: -8px;
    opacity: 0.8;
    word-wrap: break-word;
    word-break: break-word;
    white-space: normal;
    overflow-wrap: break-word;
    hyphens: auto;
    width: 100%;
    display: block;
  }

  ha-check-list-item[selected] div.headline {
    text-decoration: line-through;
    color: var(--secondary-text-color);
    font-style: italic;
  }

  ha-check-list-item[selected] ha-markdown-element {
    text-decoration: line-through;
    opacity: 0.6;
  }

  /* Checkbox styling */
  ha-check-list-item mwc-checkbox,
  ha-check-list-item ha-checkbox {
    --mdc-checkbox-size: 20px;
    --mdc-checkbox-unchecked-color: var(--secondary-text-color);
    --mdc-checkbox-checked-color: var(--primary-color);
    --mdc-checkbox-ink-color: var(--primary-color);
    --mdc-checkbox-disabled-color: var(--disabled-text-color);
    flex-shrink: 0;
  }

  /* Focus states for accessibility */
  ha-check-list-item:focus-within {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
    background-color: var(--primary-color-alpha, rgba(3, 169, 244, 0.05));
  }

  /* Section styling */
  sl-details::part(base) {
    background-color: transparent;
    border: none;
  }
  
  sl-details::part(summary) {
    margin-left: 1em;
    position: relative;
    padding: 8px 0;
  }
  
  sl-details::part(content) {
    padding: 0;
  }

  sl-details::part(header):hover {
    border-left: 4px solid var(--primary-color, #03a9f4);
  }

  .summary-container {
    display: flex;
    align-items: center;
    width: 100%;
    position: relative;
    border-left: 4px solid transparent;
    transition: border-color 0.2s ease;
  }

  .summary-text {
    flex-grow: 1;
    font-weight: 500;
    color: var(--primary-text-color);
  }

  .hide-icon {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0;
    transition: opacity 0.2s ease;
    cursor: pointer;
    color: var(--sl-color-neutral-400);
    z-index: 10;
    pointer-events: auto;
  }

  /** Necessary, because we can't perform hover callbacks on sl-details shadow root */
  .summary-container:hover .hide-icon {
    opacity: 1;
  }

  .hide-icon:hover {
    color: var(--sl-color-neutral-600);
  }
  `;
}

/**
 * This is necessary because HomeAssistant bundles (and lazy loads) their DialogTodoItemEditor,
 * so it's difficult to import, and the UI is a little unaligned. Therefore, create our own
 * so that we can support custom inputs (like label changing).
 */
class DialogTodoistItemEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      item: { type: Object },
    };
  }

  render() {
    return html`
      <sl-dialog label="Edit Item" open>
        <div>
          <sl-input
            autofocus
            label="Title"
            value="${this.item.content}"
            @sl-input=${(e) => this.updateItem('title', e.target.value)}
          ></sl-input>
          <sl-input
            label="Labels (comma-separated)"
            value="${this.item.labels.join(', ')}"
            @sl-input=${(e) => this.updateLabels(e.target.value)}
          ></sl-input>
          <sl-textarea
            resize="auto"
            label="Description"
            value="${this.item.description || ''}"
            @sl-input=${(e) => this.updateItem('description', e.target.value)}
          ></sl-textarea>
        </div>
        <sl-button slot="footer" variant="default" @click=${this.handleClose}>Cancel</sl-button>
        <sl-button slot="footer" variant="primary" @click=${this.saveItem}>Save</sl-button>
      </sl-dialog>
    `;
  }

  firstUpdated() {
    //  NOTE: This is necessary so that we handle focus correctly.
    const dialog = this.shadowRoot.querySelector('sl-dialog');
    if (dialog) {
      dialog.addEventListener('sl-request-close', (event) => {
        this.handleClose();
      });
    }
  }

  updateItem(field, value) {
    this.item = { ...this.item, [field]: value };
  }

  updateLabels(value) {
    this.item.labels = value.split(',').map(label => label.trim());
  }

  saveItem() {
    this.hass.callService(
      "rest_command",
      "todoist_update_task",
      {
        task_id: this.item.id,
        content: this.item.content,
        description: this.item.description,
        labels: this.item.labels,
      },
    );

    this.handleClose();
  }

  handleClose() {
    // Remove focus from any element inside the dialog
    const activeElement = this.shadowRoot.activeElement || document.activeElement;
    if (activeElement) {
      activeElement.blur();
    }

    this.shadowRoot.querySelector("sl-dialog").hide();
  }

  static styles = css`
    sl-dialog::part(body),
    sl-dialog::part(footer) {
      padding-top: 0;
    }

    sl-input {
      display: block;
      margin-bottom: 16px;
    }

    sl-button {
      margin: 0 8px;
    }
  `;
}

//  Register the above elements to the overall components window.
customElements.define("todoist-header", Header);
customElements.define("todoist-quick-add", TodoistQuickAdd);
customElements.define("todoist-labelled-section", TodoistLabelledSection);
customElements.define("dialog-todoist-item-editor", DialogTodoistItemEditor);
customElements.define("todoist-card-list", TodoistCardList);

//  Integrate this with the HomeAssistant dashboard.
window.customCards = window.customCards || [];
window.customCards.push({
  name: "Todoist: Labelled List",
  type: "todoist-card-list",
  description: "Custom card to organize items by label.",
  preview: true,
});