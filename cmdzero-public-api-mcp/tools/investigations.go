package tools

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/url"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	mcpcmdzero "github.com/cmdzero/cmdzero-public-api-mcp"
)

// ListInvestigationsParams defines the parameters for listing investigations.
type ListInvestigationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression (e.g. status eq 'completed'\\, severity eq 'critical'\\, contains(title\\, 'phishing'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 100\\, min 1\\, max 100)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listInvestigations(ctx context.Context, args ListInvestigationsParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	params := url.Values{}
	if args.Filter != "" {
		params.Set("filter", args.Filter)
	}
	if args.Limit > 0 {
		params.Set("limit", fmt.Sprintf("%d", args.Limit))
	}
	if args.Next != "" {
		params.Set("next", args.Next)
	}

	path := "/investigations"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListInvestigations = mcpcmdzero.MustTool(
	"list_investigations",
	"List investigations for the organization. Results are sorted by creation time (newest first). Supports OData filtering by status, severity, verdict, tags, title, and more. Use query_investigations for complex filter expressions.",
	listInvestigations,
	mcp.WithTitleAnnotation("List investigations"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryInvestigationsParams defines the parameters for querying investigations with complex filters.
type QueryInvestigationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression (e.g. status eq 'completed' and severity eq 'critical')"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 100\\, min 1\\, max 100)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryInvestigations(ctx context.Context, args QueryInvestigationsParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := make(map[string]any)
	if args.Filter != "" {
		payload["filter"] = args.Filter
	}
	if args.Limit > 0 {
		payload["limit"] = args.Limit
	}
	if args.Next != "" {
		payload["next"] = args.Next
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Query(ctx, "/investigations", bytes.NewReader(body))
}

var QueryInvestigations = mcpcmdzero.MustTool(
	"query_investigations",
	"Query investigations using the QUERY method with JSON body. Preferred over list_investigations for complex filter expressions as it avoids URL length limits and encoding issues.",
	queryInvestigations,
	mcp.WithTitleAnnotation("Query investigations"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AlertSchemaAnnotation represents a field annotation in an alert schema.
type AlertSchemaAnnotation struct {
	Path string `json:"path" jsonschema:"required,description=Dot-notation path to the field in alertData (e.g. sender.email\\, file.sha256)"`
	Type string `json:"type" jsonschema:"required,description=The type annotation for this field (e.g. EMAIL_ADDRESS\\, SHA256\\, IP_ADDRESS\\, HOSTNAME\\, URL\\, DATETIME)"`
}

// InvestigationLead represents a lead to start an investigation with.
type InvestigationLead struct {
	Type  string `json:"type" jsonschema:"required,description=Lead type (e.g. EMAIL_ADDRESS\\, IP_ADDRESS\\, HOSTNAME\\, SHA256\\, MICROSOFT_ENTRA_USER_PRINCIPAL_NAME)"`
	Value string `json:"value" jsonschema:"required,description=Lead value (e.g. user@example.com\\, 192.168.1.1)"`
}

// PostbackConfig represents a postback URL configuration for async notifications.
type PostbackConfig struct {
	URL   string `json:"url" jsonschema:"required,description=URL to receive the postback notification when the investigation completes"`
	Token string `json:"token,omitempty" jsonschema:"description=Optional token included in the postback request for verification"`
}

// StartInvestigationParams defines the parameters for starting an investigation.
type StartInvestigationParams struct {
	AlertType   string                  `json:"alertType,omitempty" jsonschema:"description=Type identifier for the alert (used with alertData to resolve schema automatically)"`
	AlertData   map[string]any          `json:"alertData,omitempty" jsonschema:"description=Alert payload containing the data to investigate"`
	AlertSchema any                     `json:"alertSchema,omitempty" jsonschema:"description=Either a catalog type string (e.g. RECORDED_FUTURE_PLAYBOOK_ALERT) or an array of schema annotations [{path\\, type}] describing data types in alertData"`
	TemplateID  string                  `json:"templateId,omitempty" jsonschema:"description=Investigation template ID to use instead of alert data. Use with leads parameter."`
	Leads       []InvestigationLead     `json:"leads,omitempty" jsonschema:"description=Initial leads when starting from a template"`
	Title       string                  `json:"title,omitempty" jsonschema:"description=Title for the investigation"`
	Postback    *PostbackConfig         `json:"postback,omitempty" jsonschema:"description=Postback URL configuration to receive notification when investigation completes"`
}

func startInvestigation(ctx context.Context, args StartInvestigationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := make(map[string]any)
	if args.AlertType != "" {
		payload["alertType"] = args.AlertType
	}
	if args.AlertData != nil {
		payload["alertData"] = args.AlertData
	}
	if args.AlertSchema != nil {
		payload["alertSchema"] = args.AlertSchema
	}
	if args.TemplateID != "" {
		payload["templateId"] = args.TemplateID
	}
	if len(args.Leads) > 0 {
		payload["leads"] = args.Leads
	}
	if args.Title != "" {
		payload["title"] = args.Title
	}
	if args.Postback != nil {
		payload["postback"] = args.Postback
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Post(ctx, "/investigations", bytes.NewReader(body))
}

var StartInvestigation = mcpcmdzero.MustTool(
	"start_investigation",
	`Start or extend an investigation in Command Zero. Supports three modes:
1. alertType + alertData: Command Zero resolves the schema from the alert type.
2. alertData + alertSchema: Provide schema annotations or a catalog type string.
3. templateId + leads: Start from a pre-configured investigation template.
Command Zero may merge the alert into an existing investigation if related. The response includes an action field indicating whether a new investigation was created or merged.`,
	startInvestigation,
	mcp.WithTitleAnnotation("Start investigation"),
)

// GetInvestigationParams defines the parameters for retrieving a single investigation.
type GetInvestigationParams struct {
	InvestigationID string `json:"investigationId" jsonschema:"required,description=The unique identifier of the investigation (UUID)"`
}

func getInvestigation(ctx context.Context, args GetInvestigationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/investigations/"+args.InvestigationID)
}

var GetInvestigation = mcpcmdzero.MustTool(
	"get_investigation",
	"Retrieve the current state and results of an investigation. When the investigation is complete, the response includes the verdict, summary, observables, alerts, assignees, and timing information.",
	getInvestigation,
	mcp.WithTitleAnnotation("Get investigation"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// UpdateInvestigationParams defines the parameters for updating an investigation.
type UpdateInvestigationParams struct {
	InvestigationID string   `json:"investigationId" jsonschema:"required,description=The unique identifier of the investigation (UUID)"`
	Assignees       []string `json:"assignees,omitempty" jsonschema:"description=Array of user IDs to assign. Replaces all current assignees. Pass empty array to clear."`
	Status          string   `json:"status,omitempty" jsonschema:"description=New status (investigating\\, completed\\, closed). Status transitions are validated."`
	Tags            []string `json:"tags,omitempty" jsonschema:"description=Array of tags. Replaces all current tags. Pass empty array to clear."`
	Severity        string   `json:"severity,omitempty" jsonschema:"description=Severity level (low\\, medium\\, high\\, critical)"`
	Sensitivity     string   `json:"sensitivity,omitempty" jsonschema:"description=Sensitivity classification (clear\\, green\\, amber\\, red)"`
	Category        string   `json:"category,omitempty" jsonschema:"description=Investigation category (e.g. Malware\\, Credential Compromise\\, Privilege Escalation)"`
	Title           string   `json:"title,omitempty" jsonschema:"description=Updated investigation title"`
}

func updateInvestigation(ctx context.Context, args UpdateInvestigationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := make(map[string]any)
	if args.Assignees != nil {
		payload["assignees"] = args.Assignees
	}
	if args.Status != "" {
		payload["status"] = args.Status
	}
	if args.Tags != nil {
		payload["tags"] = args.Tags
	}
	if args.Severity != "" {
		payload["severity"] = args.Severity
	}
	if args.Sensitivity != "" {
		payload["sensitivity"] = args.Sensitivity
	}
	if args.Category != "" {
		payload["category"] = args.Category
	}
	if args.Title != "" {
		payload["title"] = args.Title
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Patch(ctx, "/investigations/"+args.InvestigationID, bytes.NewReader(body))
}

var UpdateInvestigation = mcpcmdzero.MustTool(
	"update_investigation",
	"Update properties of an existing investigation. All fields are optional — only included fields are updated. Array fields (assignees, tags) are fully replaced. Status transitions are validated (e.g. cannot move from completed back to investigating).",
	updateInvestigation,
	mcp.WithTitleAnnotation("Update investigation"),
)

// AddInvestigationTools registers all investigation tools with the server.
func AddInvestigationTools(s *server.MCPServer) {
	AddInvestigationTemplateTools(s)
	ListInvestigations.Register(s)
	QueryInvestigations.Register(s)
	StartInvestigation.Register(s)
	GetInvestigation.Register(s)
	UpdateInvestigation.Register(s)
}
