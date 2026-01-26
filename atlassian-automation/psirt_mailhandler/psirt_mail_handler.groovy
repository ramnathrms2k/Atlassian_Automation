@groovy.transform.TypeCheckingMode(groovy.transform.TypeCheckingMode.SKIP)

import com.atlassian.jira.component.ComponentAccessor
import com.atlassian.jira.config.util.JiraHome
import com.atlassian.jira.service.services.file.FileService
import com.atlassian.jira.service.util.ServiceUtils
import com.atlassian.jira.service.util.handler.MessageUserProcessor
import com.atlassian.jira.user.ApplicationUser
import com.atlassian.jira.user.util.UserManager
import com.atlassian.mail.MailUtils
import com.atlassian.jira.issue.comments.CommentManager
import com.atlassian.jira.issue.MutableIssue
import com.atlassian.jira.service.util.handler.MessageHandlerContext
import org.apache.commons.io.FileUtils
import javax.mail.internet.MimeMessage
import javax.mail.internet.InternetAddress
import com.atlassian.jira.event.type.EventDispatchOption
import com.atlassian.jira.project.Project
import com.atlassian.jira.issue.fields.CustomField

// --- Component Accessors ---
def userManager = ComponentAccessor.userManager
def projectManager = ComponentAccessor.projectManager
def issueFactory = ComponentAccessor.issueFactory
def messageUserProcessor = ComponentAccessor.getComponent(MessageUserProcessor)
def customFieldManager = ComponentAccessor.customFieldManager
def commentManager = ComponentAccessor.commentManager
def issueManager = ComponentAccessor.issueManager

// --- Constants (Good practice for maintainability) ---
final String DEFAULT_REPORTER_USERNAME = "vmware.psirt"
final String TARGET_PROJECT_KEY = "VSRCSD"
final String CASETRAKER_ISSUE_TYPE = "Casetracker"
final String VSRC_PROJECT_NAME = "VSRC"
final String VSRC_REPORTER_CUSTOM_FIELD_NAME = "VSRC Reporter"
final String VSRC_CC_LIST_CUSTOM_FIELD_NAME = "vsrcCCList"
final String VSRC_TO_LIST_CUSTOM_FIELD_NAME = "VSRCToField"
final String IGNORED_ATTACHMENT_FILENAME = "smime.p7s"
final String BROADCOM_DOMAIN = "@broadcom.com"

// --- Helper function for handling attachments ---
def handleAttachments(MutableIssue targetIssue, JiraHome jiraHome, MessageHandlerContext context, ApplicationUser user, MimeMessage emailMessage, String ignoredAttachmentFilename) {
    def attachments = MailUtils.getAttachments(emailMessage)
    attachments.each { MailUtils.Attachment attachment ->
        if (!attachment.filename.equalsIgnoreCase(ignoredAttachmentFilename)) {
            def destination = new File(jiraHome.home, FileService.MAIL_DIR).getCanonicalFile()
            def file = FileUtils.getFile(destination, attachment.filename)
            FileUtils.writeByteArrayToFile(file, attachment.contents)
            context.createAttachment(file, attachment.filename, attachment.contentType, user, targetIssue)
            log.info("PSIRT MAILHANDLER: KEY : ${targetIssue.key} ATTACHMENT CREATED: ${attachment.filename}")
        }
    }
}

// --- Main Script Logic ---
def subject = message.getSubject() as String
def issue = ServiceUtils.findIssueObjectInString(subject)

ApplicationUser user = userManager.getUserByName(DEFAULT_REPORTER_USERNAME)
ApplicationUser mailReporter = messageUserProcessor.getAuthorFromSender(message) ?: user

def jiraHome = ComponentAccessor.getComponent(JiraHome)
def handlerContext = messageHandlerContext
def emailMessage = (MimeMessage) message // Ensure correct type

// --- Process CC and TO email addresses using JavaMail API ---
def ccAddresses = []
def toAddresses = []
if (emailMessage instanceof MimeMessage) {
    ccAddresses = emailMessage.getRecipients(MimeMessage.RecipientType.CC)?.collect { it instanceof InternetAddress ? it.address : it.toString() } ?: []
    toAddresses = emailMessage.getRecipients(MimeMessage.RecipientType.TO)?.collect { it instanceof InternetAddress ? it.address : it.toString() } ?: []
}
log.info("PSIRT MAILHANDLER: CC Addresses found: " + ccAddresses)
log.info("PSIRT MAILHANDLER: TO Addresses found: " + toAddresses)

// --- Identify Broadcom Email Addresses (for logging only) ---
def broadcomEmailAddresses = []
broadcomEmailAddresses.addAll(ccAddresses.findAll { (it as String).endsWith(BROADCOM_DOMAIN) })
broadcomEmailAddresses.addAll(toAddresses.findAll { (it as String).endsWith(BROADCOM_DOMAIN) })
broadcomEmailAddresses = broadcomEmailAddresses.unique() // Remove duplicates between TO and CC
log.info("PSIRT MAILHANDLER: Broadcom email addresses identified: " + broadcomEmailAddresses)

// --- Get Custom Field Objects ---
def vsrcReporterCustomField = customFieldManager.getCustomFieldObjectsByName(VSRC_REPORTER_CUSTOM_FIELD_NAME)?.first()
def vsrcCCListCustomField = customFieldManager.getCustomFieldObjectsByName(VSRC_CC_LIST_CUSTOM_FIELD_NAME)?.first()
def vsrcToListCustomField = customFieldManager.getCustomFieldObjectsByName(VSRC_TO_LIST_CUSTOM_FIELD_NAME)?.first()

// --- Handle Existing Issues ---
if (issue) {
    def mutableIssue = issueManager.getIssueObject(issue.id)
    if (!mutableIssue) {
        log.error("PSIRT MAILHANDLER: Could not retrieve mutable issue for ${issue.key}. Cannot proceed.")
        return
    }

    log.info("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Existing issue found in project ${mutableIssue.projectObject.name}")

    if (!mutableIssue.projectObject.name.equalsIgnoreCase(VSRC_PROJECT_NAME)) {
        log.info("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Issue is not in '${VSRC_PROJECT_NAME}', creating new issue in '${TARGET_PROJECT_KEY}'.")

        def project = projectManager.getProjectObjByKey(TARGET_PROJECT_KEY)
        if (!project) {
            log.error("PSIRT MAILHANDLER: Target project '${TARGET_PROJECT_KEY}' not found. Cannot create issue.")
            return
        }

        def newIssueObject = issueFactory.getIssue()
        newIssueObject.setProjectObject(project)
        newIssueObject.setSummary(subject)
        newIssueObject.setDescription(MailUtils.getBody(emailMessage))
        newIssueObject.setIssueTypeId(project.issueTypes.find { it.name == CASETRAKER_ISSUE_TYPE }?.id)
        
        newIssueObject.setReporter(mailReporter)

        if (vsrcReporterCustomField) {
            def sender = MailUtils.getSenders(emailMessage).first()
            newIssueObject.setCustomFieldValue(vsrcReporterCustomField, sender)
        } else {
            log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_REPORTER_CUSTOM_FIELD_NAME}' not found.")
        }
        
        // RE-INTRODUCING CC/TO FIELD PROCESSING LOGIC
        if (vsrcCCListCustomField) {
            def ccString = ccAddresses.unique().findAll { it }.join(', ')
            newIssueObject.setCustomFieldValue(vsrcCCListCustomField, ccString)
        } else {
            log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_CC_LIST_CUSTOM_FIELD_NAME}' not found.")
        }
        if (vsrcToListCustomField) {
            def toString = toAddresses.unique().findAll { it }.join(', ')
            newIssueObject.setCustomFieldValue(vsrcToListCustomField, toString)
        } else {
            log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_TO_LIST_CUSTOM_FIELD_NAME}' not found.")
        }

        def createdIssue = handlerContext.createIssue(user, newIssueObject)
        if (createdIssue) {
            def mutableCreatedIssue = issueManager.getIssueObject(createdIssue.id)
            log.info("PSIRT MAILHANDLER: KEY : ${createdIssue.key} ISSUE CREATED (from existing non-VSRC issue reference)")
            handleAttachments(mutableCreatedIssue, jiraHome, handlerContext, user, emailMessage, IGNORED_ATTACHMENT_FILENAME)
        }
        return
    }

    log.info("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Issue is in '${VSRC_PROJECT_NAME}', adding comment and attachments.")
    def body = MailUtils.getBody(emailMessage)
    commentManager.create(mutableIssue, mailReporter, body, true)

    // Update custom fields directly on the issue
    if (vsrcReporterCustomField) {
        def sender = MailUtils.getSenders(emailMessage).first()
        mutableIssue.setCustomFieldValue(vsrcReporterCustomField, sender)
    } else {
        log.warn("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Custom field '${VSRC_REPORTER_CUSTOM_FIELD_NAME}' not found.")
    }

    // RE-INTRODUCING CC/TO FIELD PROCESSING LOGIC
    def currentCCValues = mutableIssue.getCustomFieldValue(vsrcCCListCustomField)
    def ccList = []
    if (currentCCValues instanceof String) {
        ccList = currentCCValues.split(', ').toList()
    } else if (currentCCValues) {
        ccList = [currentCCValues]
    }
    def newCCValues = (ccList + ccAddresses).findAll { it }.unique()
    if (vsrcCCListCustomField) {
        def newCCString = newCCValues.join(', ')
        mutableIssue.setCustomFieldValue(vsrcCCListCustomField, newCCString)
        log.info("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Updated custom field '${vsrcCCListCustomField.name}' for existing issue with values: ${newCCString}")
    } else {
        log.warn("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Custom field '${VSRC_CC_LIST_CUSTOM_FIELD_NAME}' not found.")
    }

    def currentTOValues = mutableIssue.getCustomFieldValue(vsrcToListCustomField)
    def toList = []
    if (currentTOValues instanceof String) {
        toList = currentTOValues.split(', ').toList()
    } else if (currentTOValues) {
        toList = [currentTOValues]
    }
    def newTOValues = (toList + toAddresses).findAll { it }.unique()
    if (vsrcToListCustomField) {
        def newTOString = newTOValues.join(', ')
        mutableIssue.setCustomFieldValue(vsrcToListCustomField, newTOString)
        log.info("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Updated custom field '${vsrcToListCustomField.name}' for existing issue with values: ${newTOString}")
    } else {
        log.warn("PSIRT MAILHANDLER: KEY : ${mutableIssue.key} Custom field '${VSRC_TO_LIST_CUSTOM_FIELD_NAME}' not found.")
    }

    // Persist the changes to the issue
    issueManager.updateIssue(user, mutableIssue, EventDispatchOption.ISSUE_UPDATED, false)
    handleAttachments(mutableIssue, jiraHome, handlerContext, user, emailMessage, IGNORED_ATTACHMENT_FILENAME)

    return
}

// --- Handle New Issues ---
log.info("PSIRT MAILHANDLER: No existing issue found in subject, creating new issue in '${TARGET_PROJECT_KEY}'.")

def project = projectManager.getProjectObjByKey(TARGET_PROJECT_KEY)
if (!project) {
    log.error("PSIRT MAILHANDLER: Target project '${TARGET_PROJECT_KEY}' not found. Cannot create issue.")
    return
}

def issueObject = issueFactory.getIssue()
issueObject.setProjectObject(project)
issueObject.setSummary(subject)
issueObject.setDescription(MailUtils.getBody(emailMessage))
issueObject.setIssueTypeId(project.issueTypes.find { it.name == CASETRAKER_ISSUE_TYPE }?.id)
// FIX: Use the resolved mailReporter for the main Jira Reporter field
issueObject.setReporter(mailReporter)

if (vsrcReporterCustomField) {
    def sender = MailUtils.getSenders(emailMessage).first()
    issueObject.setCustomFieldValue(vsrcReporterCustomField, sender)
} else {
    log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_REPORTER_CUSTOM_FIELD_NAME}' not found.")
}

// RE-INTRODUCING CC/TO FIELD PROCESSING LOGIC
if (vsrcCCListCustomField) {
    def ccString = ccAddresses.unique().findAll { it }.join(', ')
    issueObject.setCustomFieldValue(vsrcCCListCustomField, ccString)
} else {
    log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_CC_LIST_CUSTOM_FIELD_NAME}' not found.")
}
if (vsrcToListCustomField) {
    def toString = toAddresses.unique().findAll { it }.join(', ')
    issueObject.setCustomFieldValue(vsrcToListCustomField, toString)
} else {
    log.warn("PSIRT MAILHANDLER: Custom field '${VSRC_TO_LIST_CUSTOM_FIELD_NAME}' not found.")
}

def createdIssue = handlerContext.createIssue(user, issueObject)
if (createdIssue) {
    def mutableCreatedIssue = issueManager.getIssueObject(createdIssue.id)
    log.info("PSIRT MAILHANDLER: KEY : ${createdIssue.key} ISSUE CREATED (from no issue reference)")
    handleAttachments(mutableCreatedIssue, jiraHome, handlerContext, user, emailMessage, IGNORED_ATTACHMENT_FILENAME)
}
