<?php

declare(strict_types=1);

namespace Drupal\plan\Entity;

use Drupal\Core\Entity\Attribute\ContentEntityType;
use Drupal\Core\Entity\ContentEntityDeleteForm;
use Drupal\Core\Entity\EntityChangedTrait;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Entity\EntityViewBuilder;
use Drupal\Core\Entity\Form\DeleteMultipleForm;
use Drupal\Core\Entity\Form\RevisionRevertForm;
use Drupal\Core\Entity\RevisionLogEntityTrait;
use Drupal\Core\Entity\Routing\RevisionHtmlRouteProvider;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\entity\Menu\DefaultEntityLocalTaskProvider;
use Drupal\entity\QueryAccess\UncacheableQueryAccessHandler;
use Drupal\entity\Revision\RevisionableContentEntityBase;
use Drupal\entity\Routing\AdminHtmlRouteProvider;
use Drupal\entity\UncacheableEntityAccessControlHandler;
use Drupal\entity\UncacheableEntityPermissionProvider;
use Drupal\plan\Form\PlanForm;
use Drupal\plan\PlanListBuilder;
use Drupal\user\EntityOwnerTrait;
use Drupal\views\EntityViewsData;

/**
 * Defines the plan entity.
 *
 * @ingroup plan
 */
#[ContentEntityType(
  id: 'plan',
  label: new TranslatableMarkup('Plan'),
  label_collection: new TranslatableMarkup('Plans'),
  label_singular: new TranslatableMarkup('plan'),
  label_plural: new TranslatableMarkup('plans'),
  entity_keys: [
    'id' => 'id',
    'revision' => 'revision_id',
    'bundle' => 'type',
    'label' => 'name',
    'owner' => 'uid',
    'uuid' => 'uuid',
    'langcode' => 'langcode',
  ],
  handlers: [
    'access' => UncacheableEntityAccessControlHandler::class,
    'list_builder' => PlanListBuilder::class,
    'permission_provider' => UncacheableEntityPermissionProvider::class,
    'query_access' => UncacheableQueryAccessHandler::class,
    'view_builder' => EntityViewBuilder::class,
    'views_data' => EntityViewsData::class,
    'form' => [
      'add' => PlanForm::class,
      'edit' => PlanForm::class,
      'delete' => ContentEntityDeleteForm::class,
      'delete-multiple-confirm' => DeleteMultipleForm::class,
      'revision-revert' => RevisionRevertForm::class,
    ],
    'route_provider' => [
      'default' => AdminHtmlRouteProvider::class,
      'revision' => RevisionHtmlRouteProvider::class,
    ],
    'local_task_provider' => [
      'default' => DefaultEntityLocalTaskProvider::class,
    ],
  ],
  links: [
    'canonical' => '/plan/{plan}',
    'add-page' => '/plan/add',
    'add-form' => '/plan/add/{plan_type}',
    'delete-form' => '/plan/{plan}/delete',
    'delete-multiple-form' => '/plan/delete',
    'edit-form' => '/plan/{plan}/edit',
    'revision' => '/plan/{plan}/revisions/{plan_revision}/view',
    'revision-revert-form' => '/plan/{plan}/revisions/{plan_revision}/revert',
    'version-history' => '/plan/{plan}/revisions',
  ],
  admin_permission: 'administer plans',
  collection_permission: 'access plan collection',
  permission_granularity: 'bundle',
  bundle_entity_type: 'plan_type',
  bundle_label: new TranslatableMarkup('Plan type'),
  base_table: 'plan',
  data_table: 'plan_field_data',
  revision_table: 'plan_revision',
  revision_data_table: 'plan_field_revision',
  translatable: TRUE,
  show_revision_ui: TRUE,
  label_count: [
    'singular' => '@count plan',
    'plural' => '@count plans',
  ],
  field_ui_base_route: 'entity.plan_type.edit_form',
  common_reference_target: TRUE,
  revision_metadata_keys: [
    'revision_user' => 'revision_user',
    'revision_created' => 'revision_created',
    'revision_log_message' => 'revision_log_message',
  ],
)]
class Plan extends RevisionableContentEntityBase implements PlanInterface {

  use EntityChangedTrait;
  use EntityOwnerTrait;
  use RevisionLogEntityTrait;

  /**
   * {@inheritdoc}
   */
  public function label() {
    return $this->getName();
  }

  /**
   * {@inheritdoc}
   */
  public function getName() {
    return $this->get('name')->value;
  }

  /**
   * {@inheritdoc}
   */
  public function setName($name) {
    $this->set('name', $name);
    return $this;
  }

  /**
   * {@inheritdoc}
   */
  public function getCreatedTime() {
    return $this->get('created')->value;
  }

  /**
   * {@inheritdoc}
   */
  public function setCreatedTime($timestamp) {
    $this->set('created', $timestamp);
    return $this;
  }

  /**
   * {@inheritdoc}
   */
  public function getBundleLabel() {
    /** @var \Drupal\plan\Entity\PlanTypeInterface $type */
    $type = $this->entityTypeManager()
      ->getStorage('plan_type')
      ->load($this->bundle());
    return $type->label();
  }

  /**
   * {@inheritdoc}
   */
  public static function getCurrentUserId() {
    return [\Drupal::currentUser()->id()];
  }

  /**
   * {@inheritdoc}
   */
  public static function getRequestTime() {
    return \Drupal::time()->getRequestTime();
  }

  /**
   * {@inheritdoc}
   */
  public static function baseFieldDefinitions(EntityTypeInterface $entity_type) {
    $fields = parent::baseFieldDefinitions($entity_type);
    $fields += static::ownerBaseFieldDefinitions($entity_type);
    $fields += static::revisionLogBaseFieldDefinitions($entity_type);

    $fields['name'] = BaseFieldDefinition::create('string')
      ->setLabel(t('Name'))
      ->setDescription(t('The name of the plan.'))
      ->setRevisionable(TRUE)
      ->setTranslatable(TRUE)
      ->setRequired(TRUE)
      ->setSetting('max_length', 255)
      ->setSetting('text_processing', 0)
      ->setDisplayOptions('view', [
        'label' => 'hidden',
        'type' => 'string',
        'weight' => -5,
      ])
      ->setDisplayOptions('form', [
        'type' => 'string_textfield',
        'weight' => -5,
      ])
      ->setDisplayConfigurable('form', TRUE);

    $fields['status'] = BaseFieldDefinition::create('state')
      ->setLabel(t('Status'))
      ->setDescription(t('Indicates the status of the plan.'))
      ->setRevisionable(TRUE)
      ->setRequired(TRUE)
      ->setSetting('max_length', 255)
      ->setDisplayOptions('view', [
        'label' => 'hidden',
        'type' => 'state_transition_form',
        'weight' => 10,
      ])
      ->setDisplayOptions('form', [
        'type' => 'options_select',
        'weight' => 11,
      ])
      ->setDisplayConfigurable('form', TRUE)
      ->setDisplayConfigurable('view', TRUE)
      ->setSetting('workflow_callback', ['\Drupal\plan\Entity\Plan', 'getWorkflowId']);

    $fields['uid'] = BaseFieldDefinition::create('entity_reference')
      ->setLabel(t('Authored by'))
      ->setDescription(t('The user ID of author of the plan.'))
      ->setRevisionable(TRUE)
      ->setSetting('target_type', 'user')
      ->setSetting('handler', 'default')
      ->setDefaultValueCallback('Drupal\plan\Entity\Plan::getCurrentUserId')
      ->setDisplayOptions('view', [
        'label' => 'hidden',
        'type' => 'author',
        'weight' => 0,
      ])
      ->setDisplayOptions('form', [
        'type' => 'entity_reference_autocomplete',
        'weight' => 12,
        'settings' => [
          'match_operator' => 'CONTAINS',
          'size' => '60',
          'autocomplete_type' => 'tags',
          'placeholder' => '',
        ],
      ])
      ->setDisplayConfigurable('form', TRUE)
      ->setDisplayConfigurable('view', TRUE);

    $fields['created'] = BaseFieldDefinition::create('created')
      ->setLabel(t('Authored on'))
      ->setDescription(t('The time that the plan was created.'))
      ->setRevisionable(TRUE)
      ->setDefaultValueCallback(static::class . '::getRequestTime')
      ->setDisplayOptions('view', [
        'label' => 'hidden',
        'type' => 'timestamp',
        'weight' => 0,
      ])
      ->setDisplayOptions('form', [
        'type' => 'datetime_timestamp',
        'weight' => 13,
      ])
      ->setDisplayConfigurable('form', TRUE);

    $fields['changed'] = BaseFieldDefinition::create('changed')
      ->setLabel(t('Changed'))
      ->setDescription(t('The time the plan was last edited.'))
      ->setRevisionable(TRUE);

    $fields['archived'] = BaseFieldDefinition::create('boolean')
      ->setLabel(t('Archived'))
      ->setDescription(t('Whether the plan is archived.'))
      ->setRevisionable(TRUE)
      ->setDefaultValue(FALSE)
      ->setSetting('on_label', 'Yes')
      ->setSetting('off_label', 'No')
      ->setDisplayOptions('view', [
        'label' => 'inline',
        'type' => 'boolean',
        'settings' => [
          'format' => 'default',
          'format_custom_false' => '',
          'format_custom_true' => '',
        ],
        'weight' => 100,
      ])
      ->setDisplayOptions('form', [
        'type' => 'boolean_checkbox',
        'settings' => [
          'display_label' => TRUE,
        ],
        'weight' => 100,
      ]);

    return $fields;
  }

  /**
   * Gets the workflow ID for the state field.
   *
   * @param \Drupal\plan\Entity\PlanInterface $plan
   *   The plan entity.
   *
   * @return string
   *   The workflow ID.
   */
  public static function getWorkflowId(PlanInterface $plan) {
    $workflow = PlanType::load($plan->bundle())->getWorkflowId();
    return $workflow;
  }

}
