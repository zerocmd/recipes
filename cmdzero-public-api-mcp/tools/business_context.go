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

// ListBusinessContextUploadsParams defines the parameters for listing business context uploads.
type ListBusinessContextUploadsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results (e.g. status eq 'active'\\, contains(name\\, 'VIP'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listBusinessContextUploads(ctx context.Context, args ListBusinessContextUploadsParams) (json.RawMessage, error) {
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

	path := "/business-context/uploads"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListBusinessContextUploads = mcpcmdzero.MustTool(
	"list_business_context_uploads",
	"List business context uploads for the organization. Returns metadata about uploads (name, status, record count) but not the actual records. Results are sorted by creation time (newest first).",
	listBusinessContextUploads,
	mcp.WithTitleAnnotation("List business context uploads"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// Note: the API returns 405 Method Not Allowed for QUERY on
// /business-context/uploads, so no query_business_context_uploads tool
// is exposed. Use list_business_context_uploads instead.

// SchemaAnnotation maps a field path in records to a catalog subject type
// (e.g. EMAIL_ADDRESS, MICROSOFT_ENTRA_USER_PRINCIPAL_NAME). Required by
// the API on business-context uploads.
type SchemaAnnotation struct {
	Path string `json:"path" jsonschema:"required,description=Dot-notation path to the field in each record (e.g. email\\, host.id)"`
	Type string `json:"type" jsonschema:"required,description=Catalog subject type for this field (e.g. EMAIL_ADDRESS\\, MICROSOFT_ENTRA_USER_PRINCIPAL_NAME\\, IP_ADDRESS\\, HOSTNAME\\, SHA256)"`
}

// UploadBusinessContextParams defines the parameters for uploading business context.
type UploadBusinessContextParams struct {
	Name    string             `json:"name" jsonschema:"required,description=Name for this business context upload"`
	Records []map[string]any   `json:"records" jsonschema:"required,description=Array of context records to upload. Each record is a JSON object with subject-specific fields."`
	Schema  []SchemaAnnotation `json:"schema" jsonschema:"required,description=Schema annotations mapping each meaningful field in records to a catalog subject type. Required by the API."`
}

func uploadBusinessContext(ctx context.Context, args UploadBusinessContextParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	body, err := json.Marshal(args)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Post(ctx, "/business-context/uploads", bytes.NewReader(body))
}

var UploadBusinessContext = mcpcmdzero.MustTool(
	"upload_business_context",
	"Upload contextual information about subjects to enrich investigations. Business context provides organizational knowledge (e.g. VIP users, critical assets, department info) that Command Zero uses during investigations.",
	uploadBusinessContext,
	mcp.WithTitleAnnotation("Upload business context"),
)

// GetBusinessContextUploadParams defines the parameters for retrieving a single upload.
type GetBusinessContextUploadParams struct {
	UploadID string `json:"uploadId" jsonschema:"required,description=The unique identifier of the business context upload (UUID)"`
}

func getBusinessContextUpload(ctx context.Context, args GetBusinessContextUploadParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/business-context/uploads/"+args.UploadID)
}

var GetBusinessContextUpload = mcpcmdzero.MustTool(
	"get_business_context_upload",
	"Retrieve details for a specific business context upload, including its name, status, record count, and processing information.",
	getBusinessContextUpload,
	mcp.WithTitleAnnotation("Get business context upload"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// ReplaceBusinessContextUploadParams defines the parameters for replacing a business context upload.
type ReplaceBusinessContextUploadParams struct {
	UploadID string             `json:"uploadId" jsonschema:"required,description=The unique identifier of the business context upload to replace (UUID)"`
	Name     string             `json:"name" jsonschema:"required,description=Name for this business context upload"`
	Records  []map[string]any   `json:"records" jsonschema:"required,description=Array of context records to replace with. Completely replaces the existing records."`
	Schema   []SchemaAnnotation `json:"schema" jsonschema:"required,description=Schema annotations mapping each meaningful field in records to a catalog subject type. Required by the API."`
}

func replaceBusinessContextUpload(ctx context.Context, args ReplaceBusinessContextUploadParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := map[string]any{
		"name":    args.Name,
		"records": args.Records,
		"schema":  args.Schema,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Put(ctx, "/business-context/uploads/"+args.UploadID, bytes.NewReader(body))
}

var ReplaceBusinessContextUpload = mcpcmdzero.MustTool(
	"replace_business_context_upload",
	"Replace a business context upload entirely. The existing records are removed and replaced with the new ones provided.",
	replaceBusinessContextUpload,
	mcp.WithTitleAnnotation("Replace business context upload"),
)

// DeleteBusinessContextUploadParams defines the parameters for deleting a business context upload.
type DeleteBusinessContextUploadParams struct {
	UploadID string `json:"uploadId" jsonschema:"required,description=The unique identifier of the business context upload to delete (UUID)"`
}

func deleteBusinessContextUpload(ctx context.Context, args DeleteBusinessContextUploadParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Delete(ctx, "/business-context/uploads/"+args.UploadID)
}

var DeleteBusinessContextUpload = mcpcmdzero.MustTool(
	"delete_business_context_upload",
	"Delete a business context upload and all its associated records. This action cannot be undone.",
	deleteBusinessContextUpload,
	mcp.WithTitleAnnotation("Delete business context upload"),
)

// AddBusinessContextTools registers all business context tools with the server.
func AddBusinessContextTools(s *server.MCPServer) {
	ListBusinessContextUploads.Register(s)
	UploadBusinessContext.Register(s)
	GetBusinessContextUpload.Register(s)
	ReplaceBusinessContextUpload.Register(s)
	DeleteBusinessContextUpload.Register(s)
}
